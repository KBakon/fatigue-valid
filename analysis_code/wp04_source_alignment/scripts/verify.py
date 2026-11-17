"""Clean rerun, Stage-1 file-access audit, projection and bootstrap checks."""
from pathlib import Path
import ast,csv,hashlib,importlib.util,json,runpy,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];WP=ROOT/'wp04_source_alignment'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audited_stage1(out):
    original=WP/'scripts/stage1.py'
    allowed={str(p.resolve()).lower() for p in (original,ROOT/'artifacts/dataset_dictionary.md',WP/'WP04_METHOD_SPEC.md')}
    source=ROOT/'data/wp01b_sources/MxD_Data_User_Study'
    reads=set()
    def hook(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        p=Path(args[0]).resolve();mode=args[1]
        if isinstance(mode,str) and ('w' in mode or 'a' in mode or 'x' in mode):return
        try:rel=p.relative_to(ROOT)
        except ValueError:return
        s=str(p).lower();reads.add(rel.as_posix())
        if s in allowed or p.is_relative_to(out) or p.is_relative_to(source):return
        raise RuntimeError('Unexpected Stage-1 read: '+str(p))
    sys.addaudithook(hook)
    sys.argv=[str(original),str(out)]
    runpy.run_path(str(original),run_name='__main__')
    (out/'verification/stage1_access_audit.json').write_text(json.dumps({'status':'PASS','project_reads':sorted(reads),'assertion':'No downstream agreement/prediction/result source opened. Source numerical projection restricted to selected Time/gyro columns.'},indent=2)+'\n')
def main():
    if len(sys.argv)>1 and sys.argv[1]=='--audit-stage1':
        audited_stage1(Path(sys.argv[2]));return
    rerun=WP/'verification/clean_rerun'
    suffix=2
    while rerun.exists():
        rerun=WP/f'verification/clean_rerun_{suffix:03d}';suffix+=1
    rerun.mkdir()
    logs=[]
    commands=[[sys.executable,'-B',str(WP/'scripts/stage0.py'),str(rerun)],
              [sys.executable,'-B',str(Path(__file__)),'--audit-stage1',str(rerun)],
              [sys.executable,'-B',str(WP/'scripts/stage2.py'),str(rerun)],
              [sys.executable,'-B',str(WP/'scripts/report.py'),str(rerun)]]
    for cmd in commands:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        logs.append({'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        (WP/'verification/clean_rerun_log.json').write_text(json.dumps(logs,indent=2)+'\n')
        assert p.returncode==0,p.stderr
    checks=[]
    for p in sorted(WP.glob('*.csv'))+sorted(WP.glob('*.sha256')):
        checks.append(dict(file=p.name,original_sha256=sha(p),rerun_sha256=sha(rerun/p.name),identical=sha(p)==sha(rerun/p.name)))
    for name in ('WP04_RESULT_SUMMARY.md','figures/WP04_mechanism.png'):
        checks.append(dict(file=name,original_sha256=sha(WP/name),rerun_sha256=sha(rerun/name),identical=sha(WP/name)==sha(rerun/name)))
    assert all(c['identical'] for c in checks)
    code=WP/'scripts/stage1.py';tree=ast.parse(code.read_text())
    imports=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
        if isinstance(n,ast.ImportFrom):imports.append(n.module)
    assert set(imports)=={'pathlib','csv','hashlib','json','sys','numpy'}
    assert not any(s in code.read_text().lower() for s in ('borg','agreement','wp02','support_class'))
    spec=importlib.util.spec_from_file_location('s1',code);s1=importlib.util.module_from_spec(spec);spec.loader.exec_module(s1)
    assert s1.COLS==['Time']+[f'IMU_{i}_{a}_dps_' for i in range(1,6) for a in ('gx','gy','gz')]
    first=next((ROOT/'data/wp01b_sources/MxD_Data_User_Study').rglob('Rep[1-5]_*.csv'))
    with first.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f);header=next(reader);idx=[header.index(c) for c in s1.COLS]
        poisoned=WP/'verification/projection_poison_test.csv'
        with poisoned.open('w',newline='',encoding='utf-8') as g:
            w=csv.writer(g);w.writerow(header)
            for row in reader:w.writerow([v if i in idx else 'UNSELECTED_NONNUMERIC_SENTINEL' for i,v in enumerate(row)])
    original=np.loadtxt(first,delimiter=',',skiprows=1,usecols=idx)
    poison=np.loadtxt(poisoned,delimiter=',',skiprows=1,usecols=idx)
    assert np.array_equal(original,poison)
    # Check literal repeated participant blocks against sufficient-statistic weights.
    with (WP/'WP04_PAIRED_TRANSITIONS.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    ids=sorted({r['participant_id'] for r in rows});rng=np.random.default_rng(20260926)
    x=np.array([[1,int(r['task']=='Composite'),int(r['transition_index']),float(r['z_arm_dominance'])] for r in rows])
    y=np.array([float(r['delta_agreement']) for r in rows]);masks=[np.array([r['participant_id']==p for r in rows]) for p in ids]
    maximum=0.
    for _ in range(20):
        draw=rng.integers(len(ids),size=len(ids));w=np.bincount(draw,minlength=len(ids))
        indices=np.concatenate([np.flatnonzero(masks[i]) for i in draw])
        literal=np.linalg.lstsq(x[indices],y[indices],rcond=None)[0]
        aa=sum(n*(x[m].T@x[m]) for n,m in zip(w,masks));bb=sum(n*(x[m].T@y[m]) for n,m in zip(w,masks))
        weighted=np.linalg.solve(aa,bb);maximum=max(maximum,float(np.max(abs(literal-weighted))))
        assert np.allclose(literal,weighted,atol=1e-12)
    assert all(int(r['zero_arm_torso_denominator'])==0 and int(r['zero_bilateral_denominator'])==0 for r in csv.DictReader((WP/'WP04_MECHANISM_FEATURES_FROZEN.csv').open(newline='')))
    result={'status':'PASS','deterministic_output_checks':checks,'stage1_import_allowlist':imports,'stage1_no_forbidden_field_references':True,'unselected_field_poison_projection_identical':True,'literal_participant_block_vs_weighted_bootstrap_draws':20,'max_coefficient_discrepancy':maximum,'audited_stage1_log':(rerun/'verification/stage1_access_audit.json').relative_to(WP).as_posix(),'zero_denominator_check':'PASS'}
    (WP/'verification/verification_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
