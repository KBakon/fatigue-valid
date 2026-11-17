"""Clean rerun, structural-only actual read audit, participant-block verification."""
from common import *
from collections import defaultdict
import ast,random,runpy,statistics,subprocess
import numpy as np
def audited_stage1(out):
    code=WP/'scripts/stage1.py'
    allowed={p.resolve() for p in (code,WP/'scripts/common.py',WP/'WP05_METHOD_SPEC.md',ROOT/'artifacts/wp02_model_predictions_blind.csv',ROOT/'artifacts/wp02_stage_a_manifest.json',out/'verification/WP05_SHARED_KEYS.csv',out/'verification/WP05_SHARED_KEYS.sha256',out/'WP05_REGIME_TABLE_FROZEN.csv')}
    reads=set()
    def hook(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        mode=args[1]
        if isinstance(mode,str) and any(x in mode for x in ('w','a','x')):return
        p=Path(args[0]).resolve()
        if not p.is_relative_to(ROOT):return
        reads.add(p.relative_to(ROOT).as_posix())
        if p not in allowed:raise RuntimeError('Nonallowlisted structural-stage read: '+str(p))
    sys.addaudithook(hook);sys.argv=[str(code),str(out)];runpy.run_path(str(code),run_name='__main__')
    save(out/'verification/stage1_access_audit.json',dict(status='PASS',project_reads=sorted(reads),allowed_read_count=len(allowed),no_empirical_validation_or_wp04_outcome_file_opened=True))
def algorithm_checks():
    rows=read(WP/'WP05_PAIRED_TRANSITIONS.csv');ids=sorted({r['participant_id'] for r in rows});rng=random.Random(20260926)
    masks=[np.array([r['participant_id']==p for r in rows]) for p in ids]
    x=np.array([[1,int(r['famB_regime']=='FAM_B_DOWN'),int(r['task']=='Composite'),int(r['famB_regime']=='FAM_B_DOWN' and r['task']=='Composite'),int(r['transition_index'])] for r in rows],float)
    y=np.array([float(r['famB_ACC_agreement']) for r in rows]);discrepancies=[]
    for _ in range(30):
        draw=[rng.randrange(len(ids)) for _ in ids];w=np.bincount(draw,minlength=len(ids));idx=np.concatenate([np.flatnonzero(masks[i]) for i in draw])
        aa=sum(n*(x[m].T@x[m]) for n,m in zip(w,masks));bb=sum(n*(x[m].T@y[m]) for n,m in zip(w,masks))
        literal=np.linalg.lstsq(x[idx],y[idx],rcond=None)[0];weighted=np.linalg.solve(aa,bb)
        discrepancies.append(float(max(abs(literal-weighted))));assert np.allclose(literal,weighted,atol=1e-12)
        # Every repeated person carries precisely the same whole block, across tasks.
        for i in range(len(ids)):
            assert np.sum([rows[k]['participant_id']==ids[i] for k in idx])==int(w[i])*int(masks[i].sum())
    # Conditional summaries: draw eligible IDs, carry their complete blocks, then select regime/task.
    checks=0
    for task in ('Composite','Harnessing','Pooled_secondary'):
        for regime in ('FAM_B_UP','FAM_B_DOWN'):
            selected=[r for r in rows if (task=='Pooled_secondary' or r['task']==task) and r['famB_regime']==regime]
            eligible=sorted({r['participant_id'] for r in selected})
            means={p:statistics.mean(float(r['famB_ACC_agreement']) for r in selected if r['participant_id']==p) for p in eligible}
            rng=random.Random(20260926)
            for _ in range(30):
                sample=[eligible[rng.randrange(len(eligible))] for p in eligible]
                via_means=statistics.mean(means[p] for p in sample);literal_means=[]
                for p in sample:
                    block=[r for r in rows if r['participant_id']==p]
                    vals=[float(r['famB_ACC_agreement']) for r in block if r['famB_regime']==regime and (task=='Pooled_secondary' or r['task']==task)]
                    literal_means.append(statistics.mean(vals))
                assert abs(via_means-statistics.mean(literal_means))<1e-14;checks+=1
    # Explicit paired prevalence keeps the two tasks inside each sampled person's difference.
    shares=read(WP/'WP05_PARTICIPANT_DOWN_SHARES.csv');lookup={(r['participant_id'],r['task']):float(r['down_share']) for r in shares}
    matched=sorted({p for p,t in lookup if t=='Composite'} & {p for p,t in lookup if t=='Harnessing'})
    rng=random.Random(20260926)
    for _ in range(30):
        draw=[matched[rng.randrange(len(matched))] for p in matched]
        paired=statistics.mean(lookup[p,'Composite']-lookup[p,'Harnessing'] for p in draw)
        separate=statistics.mean(lookup[p,'Composite'] for p in draw)-statistics.mean(lookup[p,'Harnessing'] for p in draw)
        assert abs(paired-separate)<1e-14
    return dict(status='PASS',literal_vs_sufficient_statistic_regression_draws=30,max_coefficient_discrepancy=max(discrepancies),conditional_whole_block_summary_draws=checks,matched_whole_person_prevalence_draws=30,no_transition_independence_required=True)
def main():
    if len(sys.argv)>1 and sys.argv[1]=='--audit-stage1':audited_stage1(Path(sys.argv[2]));return
    out=WP/'verification/clean_rerun';i=2
    while out.exists():out=WP/f'verification/clean_rerun_{i:03d}';i+=1
    out.mkdir();logs=[]
    commands=[[sys.executable,'-B',str(WP/'scripts/stage0.py'),str(out)],
              [sys.executable,'-B',str(Path(__file__)),'--audit-stage1',str(out)],
              [sys.executable,'-B',str(WP/'scripts/stage2.py'),str(out)],
              [sys.executable,'-B',str(WP/'scripts/audit_s1.py'),str(out)],
              [sys.executable,'-B',str(WP/'scripts/report.py'),str(out)]]
    for cmd in commands:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);logs.append(dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        save(WP/'verification/clean_rerun_log.json',logs);assert p.returncode==0,p.stderr
    checks=[]
    files=sorted(p.relative_to(WP) for p in WP.glob('*.csv'))+[Path(p) for p in ('WP05_REGIME_TABLE_FROZEN.sha256','WP05_MODEL_MAGNITUDE_STATUS.json','WP05_S1_DECISION_PATH_AUDIT.md','WP05_RESULT_SUMMARY.md','figures/WP05_regime_by_task.png','verification/stage0.json','verification/stage1_manifest.json','verification/stage2_manifest.json','verification/family_identity_checks.json','verification/S1_audit_checks.json','verification/WP05_SHARED_KEYS.csv','verification/WP05_SHARED_KEYS.sha256','verification/stage1_prediction_provenance.csv','verification/S1_existing_claim_map.csv')]
    for rel in files:
        a=digest(WP/rel);b=digest(out/rel);checks.append(dict(file=rel.as_posix(),original_sha256=a,rerun_sha256=b,identical=a==b))
    assert all(c['identical'] for c in checks)
    code=(WP/'scripts/stage1.py').read_text();tree=ast.parse(code)
    assert not any(s in code.lower() for s in ('borg','agreement','wp04_paired','wp02_transition_level','wp02_validate'))
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='load_script' for n in ast.walk(tree))
    stage1=json.loads((WP/'verification/stage1_manifest.json').read_text())
    assert digest(WP/'WP05_METHOD_SPEC.md')==stage1['method_spec_sha256']
    assert digest(WP/'WP05_REGIME_TABLE_FROZEN.csv')==(WP/'WP05_REGIME_TABLE_FROZEN.sha256').read_text().split()[0]
    result=dict(status='PASS',clean_rerun_directory=out.relative_to(WP).as_posix(),deterministic_output_checks=checks,stage1_no_empirical_field_or_loader_references=True,stage1_actual_access_audit=(out/'verification/stage1_access_audit.json').relative_to(WP).as_posix(),participant_block_audit=algorithm_checks(),frozen_method_unchanged=True,frozen_regime_seal_verified=True)
    save(WP/'verification/verification_results.json',result);print(json.dumps({k:v for k,v in result.items() if k!='deterministic_output_checks'},indent=2));print('Identical files:',len(checks))
if __name__=='__main__':main()
