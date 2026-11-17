"""Join the sealed kinematic table to frozen authoritative ACC transitions."""
from pathlib import Path
import csv,hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'wp04_source_alignment'
SEED=20260926; B=10000
FEATURES=('arm_dominance','bilateral_asymmetry','bilateral_synchrony')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def cluster_weights(ids):
    rng=np.random.default_rng(SEED);n=len(ids)
    draws=rng.integers(n,size=(B,n))
    weights=np.zeros((B,n),dtype=int)
    np.add.at(weights,(np.arange(B)[:,None],draws),1)
    assert (weights.sum(axis=1)==n).all()
    return weights
def fit(rows,predictor=None,include_index=True,variant='primary'):
    names=['intercept','Composite_minus_Harnessing']+(['transition_index'] if include_index else [])+(['z_'+predictor] if predictor else [])
    x=np.array([[1,int(r['task']=='Composite')]+([int(r['transition_index'])] if include_index else [])+([float(r['z_'+predictor])] if predictor else []) for r in rows],float)
    y=np.array([[float(r[k]) for k in ('delta_agreement','famA_ACC_agreement','famB_ACC_agreement')] for r in rows])
    ids=sorted({r['participant_id'] for r in rows}); masks=[np.array([r['participant_id']==p for r in rows]) for p in ids]
    a=np.array([x[m].T@x[m] for m in masks]);c=np.array([x[m].T@y[m] for m in masks])
    w=cluster_weights(ids)
    aa=np.einsum('bn,nij->bij',w,a);cc=np.einsum('bn,nij->bij',w,c)
    ok=np.linalg.matrix_rank(aa)==len(names)
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    boots=np.linalg.solve(aa[ok],cc[ok])
    lo,hi=np.quantile(boots,[.025,.975],axis=0)
    assert np.allclose(beta[:,0],beta[:,2]-beta[:,1])
    result=[]
    for yi,outcome in enumerate(('delta_agreement','famA_ACC_agreement','famB_ACC_agreement')):
        resid=y[:,yi]-x@beta[:,yi];sst=np.sum((y[:,yi]-np.mean(y[:,yi]))**2)
        for j,name in enumerate(names):
            p=min(1.,2*min((1+np.sum(boots[:,j,yi]<=0))/(len(boots)+1),(1+np.sum(boots[:,j,yi]>=0))/(len(boots)+1)))
            result.append(dict(variant=variant,predictor=predictor or 'none_M0',outcome=outcome,term=name,estimate=float(beta[j,yi]),ci_lower=float(lo[j,yi]),ci_upper=float(hi[j,yi]),bootstrap_sign_tail_p=float(p),holm_p='',participants=len(ids),transitions=len(rows),bootstrap_valid=int(ok.sum()),bootstrap_rank_deficient=int((~ok).sum()),descriptive_R2=float(1-resid@resid/sst) if sst else ''))
    return result
def characterize(rows,label):
    ids=sorted({r['participant_id'] for r in rows}); vals=np.full((len(ids),2),np.nan);participant=[]
    for i,p in enumerate(ids):
        for j,t in enumerate(('Composite','Harnessing')):
            xx=[float(r['arm_dominance']) for r in rows if r['participant_id']==p and r['task']==t]
            if xx:
                vals[i,j]=np.mean(xx);participant.append(dict(cohort=label,participant_id=p,task=t,segments_or_transitions=len(xx),mean_arm_dominance=float(vals[i,j])))
    w=cluster_weights(ids);finite=np.isfinite(vals);clean=np.nan_to_num(vals)
    boot=(w@clean)/(w@finite.astype(float));means=np.nanmean(vals,axis=0);records=[]
    for j,t in enumerate(('Composite','Harnessing')):
        lo,hi=np.quantile(boot[:,j],[.025,.975]);records.append(dict(cohort=label,contrast=t,participants=int(finite[:,j].sum()),estimate=float(means[j]),ci_lower=float(lo),ci_upper=float(hi)))
    matched=vals[finite.all(axis=1)];diff=matched[:,0]-matched[:,1]
    ww=cluster_weights(list(range(len(diff))));bs=ww@diff/len(diff);lo,hi=np.quantile(bs,[.025,.975])
    records.append(dict(cohort=label,contrast='Composite-minus-Harnessing matched',participants=len(diff),estimate=float(np.mean(diff)),ci_lower=float(lo),ci_upper=float(hi)))
    return records,participant
def main():
    fp=OUT/'WP04_MECHANISM_FEATURES_FROZEN.csv'; seal=(OUT/'WP04_MECHANISM_FEATURES_FROZEN.sha256').read_text().split()[0]
    assert digest(fp)==seal
    manifest=json.loads((OUT/'verification/stage1_manifest.json').read_text());assert manifest['feature_sha256']==seal
    baseline=json.loads((OUT/'verification/stage0.json').read_text());assert baseline['status']=='PASS'
    features=read(fp);fk={}
    for r in features:
        k=(r['participant_id'],r['task'],r['segment_id']);assert k not in fk;fk[k]=r
    op=ROOT/'artifacts/wp02_transition_level_results.csv'
    authoritative=json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text())['output_hashes_sha256'][op.name]
    assert digest(op)==authoritative
    outcomes=read(op); model={e:{} for e in ('ACC_A','ACC_B')}
    for r in outcomes:
        if r['endpoint_id'] not in model:continue
        key=tuple(r[k] for k in ('participant_id','task','from_segment','to_segment'))
        assert key not in model[r['endpoint_id']];model[r['endpoint_id']][key]=r
    paired_keys=sorted(model['ACC_A'].keys() & model['ACC_B'].keys()); paired=[];excluded=[]
    for key in paired_keys:
        p,t,s,nxt=key;a=model['ACC_A'][key];b=model['ACC_B'][key];f=fk.get((p,t,nxt))
        assert int(nxt[-1])==int(s[-1])+1
        if not f:
            excluded.append(dict(participant_id=p,task=t,segment_j=s,segment_j_plus_1=nxt,reason='NEXT_SEGMENT_FEATURE_UNAVAILABLE'));continue
        paired.append(dict(participant_id=p,task=t,transition_index=int(s[-1]),segment_j=s,segment_j_plus_1=nxt,famA_ACC_agreement=int(a['agreement']),famB_ACC_agreement=int(b['agreement']),delta_agreement=int(b['agreement'])-int(a['agreement']),**{k:f[k] for k in FEATURES},famA_observed_direction=int(a['observed_direction']),famB_observed_direction=int(b['observed_direction']),famA_predicted_direction=int(a['predicted_direction']),famB_predicted_direction=int(b['predicted_direction'])))
    scales={};results=[]
    for feature in FEATURES:
        xx=np.array([float(r[feature]) for r in paired if r[feature]!='']);mean=float(np.mean(xx));sd=float(np.std(xx,ddof=0));assert sd>0
        scales[feature]=dict(mean=mean,population_sd=sd,n=len(xx))
        for r in paired:r['z_'+feature]=(float(r[feature])-mean)/sd if r[feature]!='' else ''
        subset=[r for r in paired if r[feature]!='']
        if subset:results+=fit(subset,feature)
    results+=fit(paired)
    matched_ids=sorted({r['participant_id'] for r in paired if r['task']=='Composite'} & {r['participant_id'] for r in paired if r['task']=='Harnessing'})
    matched=[r for r in paired if r['participant_id'] in matched_ids]
    for feature in FEATURES:
        results+=fit([r for r in matched if r[feature]!=''],feature,variant='matched_tasks')
        results+=fit([r for r in paired if r[feature]!=''],feature,False,'omit_transition_index')
    results+=fit(matched,variant='matched_tasks')
    results+=fit(paired,include_index=False,variant='omit_transition_index')
    for outcome in ('delta_agreement','famA_ACC_agreement','famB_ACC_agreement'):
        secondary=[r for r in results if r['variant']=='primary' and r['outcome']==outcome and r['predictor'] in FEATURES[1:] and r['term']=='z_'+r['predictor']]
        ordered=sorted(secondary,key=lambda r:r['bootstrap_sign_tail_p']);prev=0
        for i,r in enumerate(ordered):prev=max(prev,min(1,(len(ordered)-i)*r['bootstrap_sign_tail_p']));r['holm_p']=prev
    write('WP04_PAIRED_TRANSITIONS.csv',paired)
    write('WP04_PRIMARY_RESULTS.csv',results)
    checks=[];pt=[]
    eligible_pt={(r['participant_id'],r['task']) for r in paired}
    eligible_features=[r for r in features if (r['participant_id'],r['task']) in eligible_pt]
    for rr,label in ((paired,'shared_next_active_segments'),(eligible_features,'eligible_participant_tasks_all_active_segments')):
        ch,pp=characterize(rr,label);checks+=ch;pt+=pp
    write('WP04_TASK_CHARACTERIZATION.csv',checks);write('WP04_PARTICIPANT_FEATURE_MEANS.csv',pt)
    counts=[]
    for t in ('Composite','Harnessing'):
        pp=[r for r in paired if r['task']==t]
        counts.append(dict(task=t,ACC_A_transitions=len([k for k in model['ACC_A'] if k[1]==t]),ACC_B_transitions=len([k for k in model['ACC_B'] if k[1]==t]),paired_before_feature=sum(k[1]==t for k in paired_keys),missing_feature_exclusions=sum(r['task']==t for r in excluded),participants=len({r['participant_id'] for r in pp}),transitions=len(pp),famA_agreement_zero=sum(r['famA_ACC_agreement']==0 for r in pp),famB_agreement_zero=sum(r['famB_ACC_agreement']==0 for r in pp),famA_observed_ties=sum(r['famA_observed_direction']==0 for r in pp),famB_observed_ties=sum(r['famB_observed_direction']==0 for r in pp),famA_prediction_ties=sum(r['famA_predicted_direction']==0 for r in pp),famB_prediction_ties=sum(r['famB_predicted_direction']==0 for r in pp)))
    write('verification/stage2_cohort_counts.csv',counts)
    if excluded:write('verification/stage2_exclusions.csv',excluded)
    else:(OUT/'verification/stage2_exclusions.csv').write_text('participant_id,task,segment_j,segment_j_plus_1,reason\n')
    att=[]
    for variant in ('primary','matched_tasks','omit_transition_index'):
        def taskcoef(pred):return next(r['estimate'] for r in results if r['variant']==variant and r['predictor']==pred and r['outcome']=='delta_agreement' and r['term']=='Composite_minus_Harnessing')
        m0=taskcoef('none_M0');m1=taskcoef('arm_dominance')
        att.append(dict(variant=variant,M0_task=m0,M1_task=m1,signed_change=m1-m0,magnitude_attenuation_percent=100*(abs(m0)-abs(m1))/abs(m0)))
    write('WP04_TASK_ATTENUATION.csv',att)
    rec=dict(status='PASS',bootstrap_unit='participant_id across all tasks',bootstrap_resamples=B,seed=SEED,random_generator='numpy.default_rng',cluster_implementation='Participant-specific XTX/XTY sufficient statistics weighted by multinomial counts from resampled participant IDs; all observations of each ID carry the same multiplicity.',participants=len({r['participant_id'] for r in paired}),transitions=len(paired),matched_task_participants=len(matched_ids),matched_task_transitions=len(matched),standardization=scales,feature_sha256_before_and_after=seal,outcome_source_sha256=authoritative,stage2_script_sha256=digest(Path(__file__)),counts=counts,secondary_status={f:'TESTED' for f in FEATURES[1:]},maximum_rank_deficient_resamples=max(r['bootstrap_rank_deficient'] for r in results))
    assert digest(fp)==seal
    (OUT/'verification/stage2_manifest.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))
if __name__=='__main__':main()
