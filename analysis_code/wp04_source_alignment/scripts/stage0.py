"""Reproduce ACC authority using frozen transition rows and existing bootstrap."""
from pathlib import Path
import csv, hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'wp04_source_alignment'
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('authority', ROOT/'scripts/wp02_validate.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
manifest, frozen = v.verify_freeze(ROOT/'artifacts')
trans = v.rows(ROOT/'artifacts/wp02_transition_level_results.csv')
sb = json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text())
for name, sha in sb['output_hashes_sha256'].items():
    assert v.digest(ROOT/'artifacts'/name)==sha
groups = {}
for r in trans:
    if r['endpoint_id'] in ('ACC_A','ACC_B'):
        groups.setdefault((r['endpoint_id'],r['task'],r['participant_id']),[]).append(int(r['agreement']))
means = {k:sum(x)/len(x) for k,x in groups.items()}
results=[]
for endpoint in ('ACC_A','ACC_B'):
    frozen_results=v.rows(ROOT/'artifacts/wp02_endpoint_results.csv')
    for task in ('Composite','Harnessing'):
        vals=[means[k] for k in sorted(means) if k[:2]==(endpoint,task)]
        est=sum(vals)/len(vals); lo,hi=v.boot_ci(vals)
        row=next(r for r in frozen_results if (r['endpoint_id'],r['task'])==(endpoint,task))
        assert max(abs(a-float(row[b])) for a,b in zip((est,lo,hi),('mean_participant_score','ci_lower','ci_upper')))<1e-10
        results.append(dict(endpoint=endpoint,contrast=task,n=len(vals),estimate=est,ci_lower=lo,ci_upper=hi))
    ids=sorted({k[2] for k in means if k[:2]==(endpoint,'Composite')} & {k[2] for k in means if k[:2]==(endpoint,'Harnessing')})
    vals=[means[(endpoint,'Composite',p)]-means[(endpoint,'Harnessing',p)] for p in ids]
    est=sum(vals)/len(vals);lo,hi=v.boot_ci(vals)
    row=next(r for r in v.rows(ROOT/'artifacts/wp02_task_pair_results.csv') if r['endpoint_id']==endpoint)
    assert max(abs(a-float(row[b])) for a,b in zip((est,lo,hi),('mean_composite_minus_harnessing','ci_lower','ci_upper')))<1e-10
    results.append(dict(endpoint=endpoint,contrast='Composite-minus-Harnessing matched',n=len(vals),estimate=est,ci_lower=lo,ci_upper=hi))
expected=[(.281,.164,.398),(.049,-.127,.219),(.258,.064,.443)]
for r, target in zip(results[3:],expected):
    assert all(abs(r[k]-x)<.00051 for k,x in zip(('estimate','ci_lower','ci_upper'),target))
used=['scripts/wp02_validate.py','artifacts/wp02_transition_level_results.csv','artifacts/wp02_endpoint_results.csv','artifacts/wp02_task_pair_results.csv','artifacts/wp02_stage_b_manifest.json']
record={'status':'PASS','bootstrap_unit':'participant','resamples':10000,'seed':20260926,'results':results,'direct_sources_sha256':{p:v.digest(ROOT/p) for p in used},'stage_a_freeze_verified':frozen}
(OUT/'verification').mkdir(exist_ok=True)
(OUT/'verification/stage0.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
