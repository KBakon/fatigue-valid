import os
from pathlib import Path
import csv,hashlib,importlib.util,inspect,json,math,random,statistics,subprocess,sys,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[2];WP=ROOT/'wp06_observed_state_magnitude';AUDIT=ROOT/'p4_independent_audit'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def write(p,rr):
    with Path(p).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def load(name):
    p=ROOT/'scripts'/f'{name}.py';s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def seal(out,names,dest):
    (out/dest).write_text(''.join(sha(out/n)+'  '+n+'\n' for n in names))
def checkseal(out,name):
    for line in (out/name).read_text().splitlines():
        h,n=line.split('  ',1);assert sha(out/n)==h,n
def snapshot():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and 'wp06_observed_state_magnitude' not in p.relative_to(ROOT).parts and '.git' not in p.relative_to(ROOT).parts}
def prep():
    before=WP/'verification/existing_before.json';assert not before.exists();save(before,snapshot())
    zpath=Path(os.environ['FATIGUE_WP06_PRIVATE_HANDOFF']);z=zipfile.ZipFile(zpath);prefix='wp06_p1_return_handoff/'
    checks=[]
    for line in z.read(prefix+'SHA256SUMS.txt').decode().splitlines():
        h,n=line.split('  ',1);assert hashlib.sha256(z.read(prefix+n)).hexdigest()==h
        checks.append(dict(member=n,sha256=h))
    AUDIT.mkdir(exist_ok=True)
    for name in ('P4_INDEPENDENT_CONTRIBUTION_VERDICT.md','PACKAGE_MANIFEST.md','SHA256SUMS.txt'):
        dest=AUDIT/name;raw=z.read(prefix+name)
        if dest.exists():assert dest.read_bytes()==raw
        else:dest.write_bytes(raw)
        assert dest.read_bytes()==raw
    save(WP/'verification/attachment.json',dict(status='PASS',zip_path=str(zpath),zip_sha256=sha(zpath),external_zip_digest_available=False,internal_checks=checks,verdict_preserved_byte_identically=True,verdict_sha256=sha(AUDIT/'P4_INDEPENDENT_CONTRIBUTION_VERDICT.md')))
    (WP/'verification/RESEARCH_STATE_BEFORE.md').write_bytes((ROOT/'RESEARCH_STATE_AND_DECISIONS.md').read_bytes())
def model(out):
    out.mkdir(parents=True,exist_ok=True);(out/'verification').mkdir(exist_ok=True)
    assert not (out/'WP06_STATE_MAGNITUDES_FROZEN.csv').exists()
    reads=set();allowed={ROOT/'scripts/wp02_predict_blind.py',WP/'scripts/wp06.py',WP/'WP06_METHOD_SPEC.md',ROOT/'artifacts/wp02_model_inputs_blind.csv',ROOT/'artifacts/wp02_model_predictions_blind.csv',ROOT/'artifacts/wp02_stage_a_manifest.json',ROOT/'artifacts/wp02_stage_b_manifest.json',ROOT/'artifacts/wp02_stage_a_freeze.sha256',ROOT/'artifacts/wp02_prediction_robustness.json',ROOT/'wp05_structural_regime/WP05_REGIME_TABLE_FROZEN.csv',ROOT/'wp05_structural_regime/WP05_REGIME_TABLE_FROZEN.sha256'}
    # Additional authorities are hashed as bytes, never interpreted as empirical evidence.
    manifest=json.loads((ROOT/'artifacts/wp02_stage_a_manifest.json').read_text())
    for group in ('authority_file_hashes_sha256','code_file_hashes_sha256','input_file_hashes_sha256'):
        allowed.update(ROOT/p for p in manifest[group])
    allowed={p.resolve() for p in allowed}
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        mode=args[1]
        if isinstance(mode,str) and any(c in mode for c in 'wax'):return
        p=Path(args[0]).resolve()
        if not p.is_relative_to(ROOT):return
        reads.add(p.relative_to(ROOT).as_posix())
        if p not in allowed and not p.is_relative_to(out):raise RuntimeError('Non-model file access: '+str(p))
    sys.addaudithook(audit)
    checkseal(ROOT/'artifacts','wp02_stage_a_freeze.sha256')
    for group in ('authority_file_hashes_sha256','code_file_hashes_sha256','input_file_hashes_sha256'):
        for p,h in manifest[group].items():assert sha(ROOT/p)==h,p
    sb=json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text());assert sb['consumed_stage_a_manifest_sha256']==sha(ROOT/'artifacts/wp02_stage_a_manifest.json')
    regime_dir=ROOT/'wp05_structural_regime';checkseal(regime_dir,'WP05_REGIME_TABLE_FROZEN.sha256');rr=read(regime_dir/'WP05_REGIME_TABLE_FROZEN.csv')
    assert len(rr)==222 and len({r['participant_id'] for r in rr})==37
    assert {t:sum(r['task']==t for r in rr) for t in ('Composite','Harnessing')}=={'Composite':121,'Harnessing':101}
    assert {g:sum(r['famB_regime']==g for r in rr) for g in ('FAM_B_UP','FAM_B_DOWN','FAM_B_TIE')}=={'FAM_B_UP':139,'FAM_B_DOWN':83,'FAM_B_TIE':0}
    m=load('wp02_predict_blind');inputs=read(ROOT/'artifacts/wp02_model_inputs_blind.csv');assert len(inputs)==521 and set(inputs[0])==m.EXPECTED_INPUT
    grid=set(m.GRID);assert len(grid)==20
    original=read(ROOT/'artifacts/wp02_model_predictions_blind.csv');lookup={r['prediction_id']:r for r in original}
    src,start=inspect.getsourcelines(m.predict);line=start+next(i for i,s in enumerate(src) if s.strip()=='ends[name] = states.copy()')
    captured={}
    def trace(frame,event,arg):
        if frame.f_code is m.predict.__code__ and event=='line' and frame.f_lineno==line:
            v=frame.f_locals;j=v['j'];name=v['name']
            for pair in m.GRID:
                prior=v['ends'][f'Rep{j-1}'][pair] if j>1 else m.E_R
                captured[v['participant'],v['task'],name,pair]=(prior,v['ew'],v['minutes'],v['states'][pair])
        return trace
    sys.settrace(trace)
    try:reproduced,_=m.predict(inputs)
    finally:sys.settrace(None)
    assert len(reproduced)==len(original)
    for r in reproduced:assert all(str(r[k])==lookup[r['prediction_id']][k] for k in m.PRED_FIELDS),r['prediction_id']
    rows=[];needed=set()
    for r in rr:
        pid=f"FAM-B|ACC_B|{r['task']}|{r['participant_id']}|{r['segment_j']}|{r['segment_j_plus_1']}";p=lookup[pid]
        pairs=json.loads(p['pair_directions_json']);assert len(pairs)==20 and {(x['lambda'],x['mu']) for x in pairs}==grid
        for pair in m.GRID:
            a,target,d,b=captured[r['participant_id'],r['task'],r['segment_j_plus_1'],pair];delta=b-a;sgn=m.sign(delta)
            expected=next(x['direction'] for x in pairs if (x['lambda'],x['mu'])==pair)
            assert sgn==expected==int(r['famB_predicted_direction']) and sgn!=0
            rows.append(dict(participant_id=r['participant_id'],task=r['task'],transition_index=r['transition_index'],from_segment=r['segment_j'],to_segment=r['segment_j_plus_1'],prediction_id=pid,**{'lambda':pair[0],'mu':pair[1]},start_state=a,target_EER=target,duration_minutes=d,duration_seconds=d*60,end_state=b,delta_state=delta,abs_delta_state=abs(delta),reconstructed_direction=sgn,WP05_frozen_regime=r['famB_regime']))
            for j in range(1,int(r['segment_j_plus_1'][-1])+1):needed.add((r['participant_id'],r['task'],f'Rep{j}'))
    assert len(rows)==4440
    source_rows=[r for r in inputs if (r['participant_id'],r['task_name'],r['segment_id']) in needed];write(out/'verification/exact_chain_inputs.csv',source_rows)
    write(out/'WP06_STATE_MAGNITUDES_FROZEN.csv',rows);seal(out,['WP06_STATE_MAGNITUDES_FROZEN.csv'],'WP06_STATE_MAGNITUDES_FROZEN.sha256')
    report=dict(status='PASS',original_prediction_rows_identically_reproduced=len(original),shared_transitions=222,participants=37,pair_rows=4440,pairs=sorted(grid),sign_mismatches=0,all20_pair_signs_robust=True,implementation='scripts/wp02_predict_blind.py::predict observed by line tracer without modifying code',trace_line=line,float_implementation='original Python binary64, no pre-verification rounding',chain_input_segments=len(source_rows),method_sha256=sha(WP/'WP06_METHOD_SPEC.md'),code_sha256=sha(Path(__file__)),input_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(allowed) if p.is_file()},state_sha256=sha(out/'WP06_STATE_MAGNITUDES_FROZEN.csv'))
    save(out/'verification/authority_and_sign_reproduction.json',report)
    save(out/'verification/stage1_access_audit.json',dict(status='PASS',reads=sorted(reads),no_empirical_outcome_file_opened=True,byte_hashes_not_semantic_reads='Authority/input files hashed for provenance; no empirical table opened.'))
    print('MODEL PASS: 4440 exact signs; states sealed')
def characterize(out):
    checkseal(out,'WP06_STATE_MAGNITUDES_FROZEN.sha256');rr=read(out/'WP06_STATE_MAGNITUDES_FROZEN.csv');summ=[];ratios=[];assign=[]
    for t in ('Composite','Harnessing'):
        for lam,mu in sorted({(float(r['lambda']),float(r['mu'])) for r in rr}):
            groups={g:[r for r in rr if r['task']==t and float(r['lambda'])==lam and float(r['mu'])==mu and r['WP05_frozen_regime']==g] for g in ('FAM_B_UP','FAM_B_DOWN')}
            values={g:np.array([float(r['abs_delta_state']) for r in rs]) for g,rs in groups.items()};stats={}
            for g,x in values.items():
                q=np.quantile(x,[0,.05,.25,.5,.75,.95,1]);stats[g]=q
                summ.append(dict(task=t,**{'lambda':lam,'mu':mu},regime=g,n_transitions=len(x),minimum=q[0],Q05=q[1],Q25=q[2],median=q[3],Q75=q[4],Q95=q[5],maximum=q[6],mean=np.mean(x)))
            u,d=stats['FAM_B_UP'],stats['FAM_B_DOWN'];assert u[3]>0
            ratios.append(dict(task=t,**{'lambda':lam,'mu':mu},median_ratio=d[3]/u[3],q95_down_to_median_up=d[5]/u[3],central_IQR_overlap=bool(max(d[2],u[2])<=min(d[4],u[4])),common_language_scale=float(np.mean(values['FAM_B_DOWN'][:,None]>=values['FAM_B_UP'][None,:])),passes_0_1_screen=bool(d[5]>=.1*u[3])))
            q1,q2=np.quantile(values['FAM_B_DOWN'],[1/3,2/3])
            for r in groups['FAM_B_DOWN']:
                x=float(r['abs_delta_state']);label='LOW' if x<=q1 else 'MIDDLE' if x<=q2 else 'HIGH'
                assign.append({k:r[k] for k in ('participant_id','task','transition_index','from_segment','to_segment','lambda','mu','abs_delta_state')}|dict(tertile=label,q1=float(q1),q2=float(q2)))
    write(out/'WP06_MODEL_SCALE_SUMMARY.csv',summ);write(out/'WP06_PAIR_SCALE_RATIOS.csv',ratios);write(out/'WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.csv',assign)
    seal(out,['WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.csv'],'WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.sha256')
    seal(out,['WP06_MODEL_SCALE_SUMMARY.csv','WP06_PAIR_SCALE_RATIOS.csv','WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.csv'],'WP06_MODEL_ONLY_SUMMARIES.sha256')
    print('MODEL-ONLY characterization and assignments sealed')
def empirical(out):
    checkseal(out,'WP06_STATE_MAGNITUDES_FROZEN.sha256');checkseal(out,'WP06_MODEL_ONLY_SUMMARIES.sha256');checkseal(out,'WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.sha256')
    v=load('wp02_validate');sb=json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text())
    for n,h in sb['output_hashes_sha256'].items():assert sha(ROOT/'artifacts'/n)==h
    evidence=read(ROOT/'artifacts/wp02_transition_level_results.csv');lookup={(r['participant_id'],r['task'],r['from_segment'],r['to_segment']):r for r in evidence if r['endpoint_id']=='ACC_B'}
    a=read(out/'WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.csv');states=read(out/'WP06_STATE_MAGNITUDES_FROZEN.csv');result=[];cache={}
    for t in ('Composite','Harnessing'):
        for lam,mu in sorted({(float(r['lambda']),float(r['mu'])) for r in a}):
            for group in ('LOW','MIDDLE','HIGH','UP_REFERENCE'):
                rr=[r for r in (states if group=='UP_REFERENCE' else a) if r['task']==t and float(r['lambda'])==lam and float(r['mu'])==mu and (r['WP05_frozen_regime']=='FAM_B_UP' if group=='UP_REFERENCE' else r['tertile']==group)]
                by={}
                for r in rr:
                    e=lookup[r['participant_id'],t,r['from_segment'],r['to_segment']];assert int(e['predicted_direction'])==(1 if group=='UP_REFERENCE' else -1)
                    by.setdefault(r['participant_id'],[]).append(int(e['agreement']))
                means=[statistics.mean(x) for p,x in sorted(by.items())];key=tuple(means)
                if means:
                    if key not in cache:cache[key]=v.boot_ci(means)
                    lo,hi=cache[key];estimate=statistics.mean(means)
                else:lo=hi=estimate=''
                result.append(dict(task=t,**{'lambda':lam,'mu':mu},group=group,participants=len(means),transitions=len(rr),estimate=estimate,ci_lower=lo,ci_upper=hi,status='NOT_ESTIMABLE' if not means else 'NEGATIVE_CI' if hi<0 else 'POSITIVE_CI' if lo>0 else 'ZERO_SPANNING'))
    write(out/'WP06_DOWN_TERTILE_AGREEMENT.csv',result)
    ratios=read(out/'WP06_PAIR_SCALE_RATIOS.csv');counts={}
    for t in ('Composite','Harnessing'):
        rs=[r for r in ratios if r['task']==t];high=[r for r in result if r['task']==t and r['group']=='HIGH']
        counts[t]=dict(screen_pass_pairs=sum(float(r['q95_down_to_median_up'])>=.1 for r in rs),screen_below_pairs=sum(float(r['q95_down_to_median_up'])<.1 for r in rs),high_negative_estimate_pairs=sum(r['estimate']!='' and r['estimate']<0 for r in high),high_negative_CI_pairs=sum(r['ci_upper']!='' and r['ci_upper']<0 for r in high),high_nonestimable_pairs=sum(r['status']=='NOT_ESTIMABLE' for r in high),high_zero_spanning_pairs=sum(r['status']=='ZERO_SPANNING' for r in high))
    A1=all(c['screen_pass_pairs']>=18 for c in counts.values());A2=all(c['high_negative_CI_pairs']>=18 for c in counts.values());B=all(c['screen_below_pairs']>=18 for c in counts.values())
    case='COMPARABLE_SCALE_SUPPORTED' if A1 and A2 else 'DOWN_NUMERICALLY_NEGLIGIBLE' if B else 'MIXED_MAGNITUDE_EVIDENCE'
    save(out/'WP06_MAGNITUDE_CLASSIFICATION.json',dict(classification=case,case='A' if A1 and A2 else 'B' if B else 'C',A1=A1,A2_conservative_negative_upper_CI=A2,B=B,counts=counts,threshold_interpretation='0.1 is solely the user-prespecified model-internal order-of-magnitude screen; not physiological/practical importance',no_final_G2_or_scientific_magnitude_verdict=True))
    save(out/'verification/empirical_provenance.json',dict(status='PASS',outcome_source_sha256=sha(ROOT/'artifacts/wp02_transition_level_results.csv'),bootstrap_function='original wp02_validate.boot_ci',seed=20260926,resamples=10000,bootstrap_unit='participant ID carrying all rows, conditional participant mean then equally weighted mean',unique_score_vectors_bootstrapped=len(cache)))
    print(case,counts)
if __name__=='__main__':
    action=sys.argv[1];out=Path(sys.argv[2]) if len(sys.argv)>2 else WP
    {'prep':prep,'model':lambda:model(out),'characterize':lambda:characterize(out),'empirical':lambda:empirical(out)}[action]()
