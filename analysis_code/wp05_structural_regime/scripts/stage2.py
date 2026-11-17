"""Empirical diagnostic calculations after structural-table sealing."""
from common import *
from collections import defaultdict
import random,statistics
import numpy as np
SEED=20260926;NBOOT=10000
REGIMES=('FAM_B_UP','FAM_B_DOWN')
OUTCOMES=('famA_ACC_agreement','famB_ACC_agreement','delta_agreement')
def participant_means(rows,outcome):
    groups=defaultdict(list)
    for r in rows:groups[r['participant_id']].append(float(r[outcome]))
    return {p:statistics.mean(x) for p,x in sorted(groups.items())}
def summary(values,v):
    if not values:return dict(participants=0,estimate='',ci_lower='',ci_upper='',status='NOT_TESTABLE')
    est=statistics.mean(values);lo,hi=v.boot_ci(values)
    status='SUPPORTED' if lo>0 else 'DIRECTIONALLY_CONTRADICTED' if hi<0 else 'EVIDENCE_INSUFFICIENT'
    return dict(participants=len(values),estimate=est,ci_lower=lo,ci_upper=hi,status=status)
def weights(ids):
    # Identical participant draws across all models of the same cohort.
    rng=random.Random(SEED);n=len(ids);w=np.zeros((NBOOT,n),dtype=int)
    for b in range(NBOOT):
        for _ in ids:w[b,rng.randrange(n)]+=1
    assert np.all(w.sum(axis=1)==n)
    return w
def regression(rows,with_index,variant):
    rows=[r for r in rows if r['famB_regime'] in REGIMES]
    names=['intercept','DOWN','Composite_minus_Harnessing','DOWN_x_Composite']+(['transition_index'] if with_index else [])
    x=np.array([[1,int(r['famB_regime']=='FAM_B_DOWN'),int(r['task']=='Composite'),int(r['famB_regime']=='FAM_B_DOWN' and r['task']=='Composite')]+([int(r['transition_index'])] if with_index else []) for r in rows],float)
    y=np.array([r['famB_ACC_agreement'] for r in rows],float)
    ids=sorted({r['participant_id'] for r in rows});masks=[np.array([r['participant_id']==p for r in rows]) for p in ids]
    a=np.array([x[m].T@x[m] for m in masks]);c=np.array([x[m].T@y[m] for m in masks]);w=weights(ids)
    aa=np.einsum('bn,nij->bij',w,a);cc=np.einsum('bn,ni->bi',w,c)
    ok=np.linalg.matrix_rank(aa)==len(names)
    assert np.linalg.matrix_rank(x)==len(names)
    beta=np.linalg.lstsq(x,y,rcond=None)[0];boots=np.linalg.solve(aa[ok],cc[ok,:,None])[:,:,0]
    r2=1-np.sum((y-x@beta)**2)/np.sum((y-np.mean(y))**2)
    results=[]
    for j,name in enumerate(names+['Composite_minus_Harnessing_within_DOWN']):
        if j==len(names):estimate=beta[2]+beta[3];dist=boots[:,2]+boots[:,3]
        else:estimate=beta[j];dist=boots[:,j]
        lo,hi=np.quantile(dist,[.025,.975]);results.append(dict(variant=variant,term=name,estimate=float(estimate),ci_lower=float(lo),ci_upper=float(hi),participants=len(ids),transitions=len(rows),bootstrap_valid=int(ok.sum()),bootstrap_rank_deficient=int((~ok).sum()),descriptive_R2=float(r2)))
    return results
def main():
    out=output();fp=out/'WP05_REGIME_TABLE_FROZEN.csv';seal=(out/'WP05_REGIME_TABLE_FROZEN.sha256').read_text().split()[0]
    assert digest(fp)==seal
    stage1=json.loads((out/'verification/stage1_manifest.json').read_text());assert stage1['regime_sha256']==seal
    assert digest(WP/'WP05_METHOD_SPEC.md')==stage1['method_spec_sha256']
    assert json.loads((out/'verification/stage0.json').read_text())['status']=='PASS'
    source=ROOT/'artifacts/wp02_transition_level_results.csv'
    sb=json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text())
    assert digest(source)==sb['output_hashes_sha256'][source.name]
    model={e:{} for e in ('ACC_A','ACC_B')}
    for r in read(source):
        if r['endpoint_id'] in model:
            k=(r['participant_id'],r['task'],r['from_segment'],r['to_segment']);assert k not in model[r['endpoint_id']];model[r['endpoint_id']][k]=r
    joined=[]
    for r in read(fp):
        k=key(r);a=model['ACC_A'][k];b=model['ACC_B'][k]
        observed=int(a['observed_direction']);assert observed==int(b['observed_direction'])
        assert int(r['famA_predicted_direction'])==int(a['predicted_direction'])==1
        assert int(r['famB_predicted_direction'])==int(b['predicted_direction'])
        for m,pred in ((a,int(r['famA_predicted_direction'])),(b,int(r['famB_predicted_direction']))):
            expected=0 if observed==0 or pred==0 else (1 if observed==pred else -1)
            assert expected==int(m['agreement'])
        aa=int(a['agreement']);bb=int(b['agreement'])
        joined.append(r|dict(observed_direction=observed,famA_ACC_agreement=aa,famB_ACC_agreement=bb,delta_agreement=bb-aa))
    write(out/'WP05_PAIRED_TRANSITIONS.csv',joined)
    comp={r['participant_id'] for r in joined if r['task']=='Composite'};harn={r['participant_id'] for r in joined if r['task']=='Harnessing'}
    matched=sorted(comp & harn);assert len(matched)==22
    supports=[];participant_rows=[];observed_counts=[]
    v=load_script('wp02_validate')
    for cohort,rr in (('shared',joined),('matched_tasks',[r for r in joined if r['participant_id'] in matched])):
        for task in ('Composite','Harnessing','Pooled_secondary'):
            for regime in REGIMES:
                group=[r for r in rr if r['famB_regime']==regime and (task=='Pooled_secondary' or r['task']==task)]
                observed_counts.append(dict(cohort=cohort,task=task,famB_regime=regime,participants=len({r['participant_id'] for r in group}),transitions=len(group),observed_down=sum(r['observed_direction']==-1 for r in group),observed_tie=sum(r['observed_direction']==0 for r in group),observed_up=sum(r['observed_direction']==1 for r in group)))
                for outcome in OUTCOMES:
                    means=participant_means(group,outcome)
                    supports.append(dict(cohort=cohort,task=task,famB_regime=regime,outcome=outcome,transitions=len(group),**summary(list(means.values()),v)))
                    for p,m in means.items():participant_rows.append(dict(cohort=cohort,task=task,famB_regime=regime,outcome=outcome,participant_id=p,eligible_transitions=sum(r['participant_id']==p for r in group),participant_mean=m))
    write(out/'WP05_REGIME_SUPPORT.csv',supports);write(out/'WP05_PARTICIPANT_REGIME_MEANS.csv',participant_rows);write(out/'WP05_BORG_DIRECTION_COUNTS.csv',observed_counts)
    prevalence=[];shares={}
    for p in sorted(comp|harn):
        for t in ('Composite','Harnessing'):
            rr=[r for r in joined if r['participant_id']==p and r['task']==t]
            if not rr:continue
            down=sum(r['famB_regime']=='FAM_B_DOWN' for r in rr);shares[p,t]=down/len(rr)
            prevalence.append(dict(participant_id=p,task=t,down_transitions=down,eligible_transitions=len(rr),down_share=down/len(rr)))
    write(out/'WP05_PARTICIPANT_DOWN_SHARES.csv',prevalence)
    prev_results=[]
    def prevalence_summary(vals):
        ss=summary(vals,v)
        return {k:ss[k] for k in ('participants','estimate','ci_lower','ci_upper')}
    for cohort,ids in (('shared',sorted(comp|harn)),('matched_tasks',matched)):
        for t in ('Composite','Harnessing'):
            vals=[shares[p,t] for p in ids if (p,t) in shares]
            prev_results.append(dict(cohort=cohort,contrast=t,**prevalence_summary(vals)))
        diff=[shares[p,'Composite']-shares[p,'Harnessing'] for p in matched]
        prev_results.append(dict(cohort=cohort,contrast='Composite-minus-Harnessing matched',**prevalence_summary(diff)))
    write(out/'WP05_REGIME_PREVALENCE.csv',prev_results)
    regs=[]
    for cohort,rr in (('shared',joined),('matched_tasks',[r for r in joined if r['participant_id'] in matched])):
        regs+=regression(rr,True,cohort);regs+=regression(rr,False,cohort+'_omit_transition_index')
    write(out/'WP05_REGRESSION_RESULTS.csv',regs)
    contrast=[r for r in supports if r['outcome']=='delta_agreement']
    write(out/'WP05_FAMILY_CONTRAST.csv',contrast)
    up=[r for r in joined if r['famB_regime']=='FAM_B_UP'];down=[r for r in joined if r['famB_regime']=='FAM_B_DOWN'];ties=[r for r in joined if r['famB_regime']=='FAM_B_TIE']
    assert all(r['famA_predicted_direction']==r['famB_predicted_direction'] for r in up)
    assert all(r['delta_agreement']==0 for r in up)
    assert all(r['delta_agreement']==-2*r['observed_direction'] for r in down)
    assert not ties,'A TIE exists: report and verify its possible family disagreement explicitly'
    family=dict(status='PASS',UP_prediction_identity=True,UP_agreement_identity=True,DOWN_delta_equals_minus_two_observed_sign=True,tie_transitions=len(ties),family_disagreement_transitions=sum(r['delta_agreement']!=0 for r in joined),disagreement_outside_DOWN=sum(r['delta_agreement']!=0 and r['famB_regime']!='FAM_B_DOWN' for r in joined),algebra='Scoring is agreement=predicted_sign*observed_sign for signs in {-1,0,+1}. A=+1 on all shared rows. UP B=+1 implies delta=0. DOWN B=-1 implies delta=(-1-1)*observed_sign=-2*observed_sign. No TIE regime exists here.')
    save(out/'verification/family_identity_checks.json',family)
    record=dict(status='PASS',participants=37,transitions=222,matched_task_participants=22,matched_task_transitions=sum(r['participant_id'] in matched for r in joined),regime_sha256_before_after=seal,authority_transition_sha256=digest(source),code_sha256=digest(Path(__file__)),bootstrap_unit='participant ID jointly carrying all eligible transitions and tasks; task/regime conditional summaries draw eligible IDs for that group',bootstrap_seed=SEED,bootstrap_resamples=NBOOT,regression_rng='Python random.Random matching original seed/generator; weighted participant sufficient statistics',regression_max_rank_deficient=max(r['bootstrap_rank_deficient'] for r in regs),pooled_summary='Mean all regime transitions within each participant across tasks, then equally weight participants; no duplicate people',exact_family_checks=family)
    assert digest(fp)==seal;save(out/'verification/stage2_manifest.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()
