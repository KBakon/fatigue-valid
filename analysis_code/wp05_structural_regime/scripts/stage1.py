"""Deterministic structural classification from original predictions and keys."""
from common import *
from collections import Counter
def main():
    out=output();target=out/'WP05_REGIME_TABLE_FROZEN.csv';assert not target.exists(),'Write-once structural freeze already exists'
    keys=out/'verification/WP05_SHARED_KEYS.csv'
    assert digest(keys)==(out/'verification/WP05_SHARED_KEYS.sha256').read_text().split()[0]
    source=ROOT/'artifacts/wp02_model_predictions_blind.csv'
    manifest=json.loads((ROOT/'artifacts/wp02_stage_a_manifest.json').read_text())
    assert digest(source)==manifest['prediction_artifact_sha256']
    predictions=read(source);lookup={}
    for r in predictions:
        if r['endpoint_id'] in ('ACC_A','ACC_B'):
            k=(r['participant_id'],r['task'],r['from_segment'],r['to_segment'],r['endpoint_id']);assert k not in lookup;lookup[k]=r
    grid={(lam,mu) for lam in (2,4,6,8,10) for mu in (.5,1,1.5,2)};table=[];provenance=[]
    for r in read(keys):
        k=key(r);a=lookup[(*k,'ACC_A')];b=lookup[(*k,'ACC_B')]
        assert a['prediction_status']=='STRUCTURAL_ROBUST_PREDICTION' and int(a['predicted_direction'])==1
        assert b['prediction_status']=='PARAMETER_ROBUST_PREDICTION' and int(b['n_parameter_pairs'])==20
        pairs=json.loads(b['pair_directions_json'])
        assert len(pairs)==20 and {(x['lambda'],x['mu']) for x in pairs}==grid
        d=int(b['predicted_direction']);assert d in (-1,0,1) and {x['direction'] for x in pairs}=={d}
        regime={1:'FAM_B_UP',-1:'FAM_B_DOWN',0:'FAM_B_TIE'}[d]
        table.append(r|dict(famA_predicted_direction=1,famB_predicted_direction=d,famB_regime=regime))
        provenance.append(r|dict(famA_prediction_id=a['prediction_id'],famB_prediction_id=b['prediction_id'],verified_unique_parameter_pairs=20,all_pair_directions_identical=True,pair_entry_fields=';'.join(sorted(pairs[0]))))
    table.sort(key=key);write(target,table)
    (out/'WP05_REGIME_TABLE_FROZEN.sha256').write_text(digest(target)+'  '+target.name+'\n')
    counts=[]
    for t in ('Composite','Harnessing'):
        for index in ('ALL','1','2','3','4'):
            for regime in ('FAM_B_UP','FAM_B_DOWN','FAM_B_TIE'):
                rr=[r for r in table if r['task']==t and (index=='ALL' or str(r['transition_index'])==index) and r['famB_regime']==regime]
                counts.append(dict(task=t,transition_index=index,famB_regime=regime,participants=len({r['participant_id'] for r in rr}),transitions=len(rr)))
    write(out/'WP05_REGIME_COUNTS.csv',counts);write(out/'verification/stage1_prediction_provenance.csv',provenance)
    schemas=Counter(tuple(sorted(x)) for p in predictions if p['endpoint_id']=='ACC_B' for x in json.loads(p['pair_directions_json']))
    assert set(schemas)=={('direction','lambda','mu')}
    save(out/'WP05_MODEL_MAGNITUDE_STATUS.json',dict(status='NOT_TESTABLE',reason='Frozen observed ACC prediction artifact stores only per-pair lambda, mu and direction; no signed state changes or endpoint states. Obtaining magnitudes would require rerunning original propagation, forbidden for this component. WP-03 states are synthetic scenario values, not observed-transition magnitudes.',prediction_columns=list(predictions[0]),per_pair_schema_counts=[dict(fields=list(k),entries=v) for k,v in schemas.items()],tertiles='NOT_TESTABLE; no model-only magnitude is available'))
    spec=WP/'WP05_METHOD_SPEC.md'
    record=dict(status='PASS',rows=len(table),participants=len({r['participant_id'] for r in table}),verified_pairs_per_transition=20,regime_sha256=digest(target),method_spec_sha256=digest(spec),stage1_code_sha256=digest(Path(__file__)),common_code_sha256=digest(Path(__file__).with_name('common.py')),input_hashes={str(source.relative_to(ROOT)):digest(source),'keys_only_cohort':digest(keys),'prediction_manifest':digest(ROOT/'artifacts/wp02_stage_a_manifest.json')},input_access_statement='Only keys-only shared membership, its seal, original frozen prediction table, prediction manifest, method specification, and own script/helper hashes are read. No empirical validation file is opened by Stage 1. This is a structural classification in a post-WP04 diagnostic analysis, not discovery blindness.')
    save(out/'verification/stage1_manifest.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()
