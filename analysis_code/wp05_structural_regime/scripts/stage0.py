"""Reproduce original ACC authority and reconcile exact shared keys."""
from common import *
from collections import defaultdict
import statistics
def main():
    out=output();v=load_script('wp02_validate')
    manifest,frozen=v.verify_freeze(ROOT/'artifacts')
    sb=json.loads((ROOT/'artifacts/wp02_stage_b_manifest.json').read_text())
    for name,sha in sb['output_hashes_sha256'].items():assert digest(ROOT/'artifacts'/name)==sha
    wp4=ROOT/'wp04_source_alignment';status=json.loads((wp4/'verification/SAVE_STATUS.json').read_text());assert status['status']=='VERIFIED_SAVED'
    assert digest(wp4/'verification/OUTPUT_MANIFEST.csv')==status['manifest_sha256']
    for r in read(wp4/'verification/OUTPUT_MANIFEST.csv'):assert digest(wp4/r['path'])==r['sha256'],r['path']
    transitions=read(ROOT/'artifacts/wp02_transition_level_results.csv');groups=defaultdict(list);models={'ACC_A':{},'ACC_B':{}}
    for r in transitions:
        e=r['endpoint_id']
        if e not in models:continue
        k=(r['participant_id'],r['task'],r['from_segment'],r['to_segment'])
        assert k not in models[e];models[e][k]=r
        groups[e,r['task'],r['participant_id']].append(int(r['agreement']))
    means={k:statistics.mean(vals) for k,vals in groups.items()};results=[]
    original=read(ROOT/'artifacts/wp02_endpoint_results.csv');pairs=read(ROOT/'artifacts/wp02_task_pair_results.csv')
    for e in models:
        for t in ('Composite','Harnessing'):
            vals=[means[k] for k in sorted(means) if k[:2]==(e,t)];est=statistics.mean(vals);lo,hi=v.boot_ci(vals)
            r=next(r for r in original if (r['endpoint_id'],r['task'])==(e,t))
            assert all(abs(x-float(r[k]))<1e-10 for x,k in zip((est,lo,hi),('mean_participant_score','ci_lower','ci_upper')))
            results.append(dict(endpoint=e,contrast=t,participants=len(vals),estimate=est,ci_lower=lo,ci_upper=hi))
        ids=sorted({k[2] for k in means if k[:2]==(e,'Composite')} & {k[2] for k in means if k[:2]==(e,'Harnessing')})
        vals=[means[e,'Composite',p]-means[e,'Harnessing',p] for p in ids];est=statistics.mean(vals);lo,hi=v.boot_ci(vals)
        r=next(r for r in pairs if r['endpoint_id']==e)
        assert all(abs(x-float(r[k]))<1e-10 for x,k in zip((est,lo,hi),('mean_composite_minus_harnessing','ci_lower','ci_upper')))
        results.append(dict(endpoint=e,contrast='Composite-minus-Harnessing matched',participants=len(ids),estimate=est,ci_lower=lo,ci_upper=hi))
    for r,target in zip(results[3:],((.281250,.164062,.398438),(.049383,-.126543,.219136),(.257576,.064394,.443182))):
        assert all(abs(r[k]-v)<.000001 for k,v in zip(('estimate','ci_lower','ci_upper'),target))
    source=wp4/'WP04_PAIRED_TRANSITIONS.csv'
    fields=['participant_id','task','transition_index','segment_j','segment_j_plus_1']
    # This is Stage 0, not the structural classification process. Only keys are retained.
    with source.open(newline='',encoding='utf-8') as f:
        reader=csv.reader(f);header=next(reader);idx=[header.index(k) for k in fields]
        cohort=[dict(zip(fields,(r[i] for i in idx))) for r in reader]
    shared=set(models['ACC_A'])&set(models['ACC_B']);assert {key(r) for r in cohort}==shared
    assert len(cohort)==len(shared)==222;assert len({r['participant_id'] for r in cohort})==37
    counts=[]
    for t,np_,nt in [('Composite',32,121),('Harnessing',27,101)]:
        rr=[r for r in cohort if r['task']==t]
        assert len(rr)==nt and len({r['participant_id'] for r in rr})==np_
        counts.append(dict(task=t,participants=np_,transitions=nt))
    assert all(int(models['ACC_A'][k]['predicted_direction'])==1 for k in shared)
    cohort.sort(key=key);kp=out/'verification/WP05_SHARED_KEYS.csv';write(kp,cohort,fields)
    (out/'verification/WP05_SHARED_KEYS.sha256').write_text(digest(kp)+'  '+kp.name+'\n')
    used=['artifacts/wp02_model_predictions_blind.csv','artifacts/wp02_transition_level_results.csv','artifacts/wp02_endpoint_results.csv','artifacts/wp02_task_pair_results.csv','artifacts/wp02_stage_a_manifest.json','artifacts/wp02_stage_b_manifest.json','scripts/wp02_validate.py','wp04_source_alignment/WP04_PAIRED_TRANSITIONS.csv','wp04_source_alignment/verification/OUTPUT_MANIFEST.csv']
    record=dict(status='PASS',results=results,shared_participants=37,shared_transitions=222,cohort_by_task=counts,wp04_manifest_verified_files=status['listed_files'],source_hashes={p:digest(ROOT/p) for p in used},keys_sha256=digest(kp),bootstrap_unit='participant',bootstrap_resamples=10000,bootstrap_seed=20260926)
    save(out/'verification/stage0.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()
