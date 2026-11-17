"""Unchanged frozen S1 and the requested no-decrease diagnostic counterfactual."""
from common import *
from decimal import Decimal,localcontext
def main():
    out=output();m=load_script('wp03_evaluate_schedules');s=m.load_frozen(ROOT/'artifacts/wp03_scenario_inputs.json')
    saved=read(ROOT/'artifacts/wp03_schedule_evaluations.csv')
    claim_map_path=ROOT/'artifacts/wp03_before_after_claim_map.csv'
    claim_map=[r for r in read(claim_map_path) if r['model_family']=='FAM-B' and r['scenario_id']=='S1']
    assert len(claim_map)==3 and all(r['required_claim_tags']=='ACC' for r in claim_map)
    write(out/'verification/S1_existing_claim_map.csv',claim_map)
    records=[];traces=[];matched_rows=0
    with localcontext() as ctx:
        ctx.prec=100
        er=Decimal(str(s['E_R_kcal_per_min']));el=Decimal(str(s['E_L_kcal_per_min']));eh=Decimal(str(s['E_H_kcal_per_min']));d=Decimal(str(s['D_minutes']))
        assert er<el<eh
        for lam,mu in m.GRID:
            info={};cf={}
            for order,seq in (('L_then_H',('L','H')),('H_then_L',('H','L'))):
                ev=m.evaluate_b(seq,s,lam,mu);info[order]=ev
                sched='S1_A' if order=='L_then_H' else 'S1_B'
                r=next(r for r in saved if r['model_family']=='FAM-B' and r['scenario_id']=='S1' and r['schedule_id']==sched and float(r['lambda_per_min'])==lam and float(r['mu_per_min'])==mu)
                for field in ('state_after_first_manual_kcal_per_min','state_after_second_manual_kcal_per_min','peak_manual_state_kcal_per_min'):assert Decimal(ev[field])==Decimal(r[field])
                matched_rows+=1;source_state=er;counter_state=er;counter_ends=[];source_downs=0
                for j,label in enumerate(seq,1):
                    target=el if label=='L' else eh
                    nxt=m.work_update(source_state,target,d,Decimal(lam),Decimal(str(mu)))
                    proposed=m.work_update(counter_state,target,d,Decimal(lam),Decimal(str(mu)))
                    accepted=max(counter_state,proposed)
                    source_downs+=nxt<source_state
                    traces.append(dict(lambda_per_min=lam,mu_per_min=mu,order=order,step=j,active_target=label,target_kcal_per_min=str(target),source_prior=str(source_state),source_rate_per_min=str(Decimal(lam) if target>=source_state else Decimal(str(mu))),source_next=str(nxt),source_direction=(nxt>source_state)-(nxt<source_state),counterfactual_prior=str(counter_state),counterfactual_candidate=str(proposed),counterfactual_next=str(accepted),counterfactual_direction=(accepted>counter_state)-(accepted<counter_state)))
                    source_state=nxt;counter_state=accepted;counter_ends.append(accepted)
                cf[order]=dict(first=counter_ends[0],second=counter_ends[1],peak=max(counter_ends),source_down_transitions=source_downs)
            lh=info['L_then_H']['objective'];hl=info['H_then_L']['objective'];gap=lh-hl
            cf_gap=cf['L_then_H']['peak']-cf['H_then_L']['peak']
            q=(-Decimal(lam)*d).exp();closed=(el-er)*(1-q)*q
            assert gap>0 and cf_gap==gap
            assert abs(gap-closed)<Decimal('1e-97')
            assert cf['L_then_H']['source_down_transitions']==0 and cf['H_then_L']['source_down_transitions']==1
            records.append(dict(lambda_per_min=lam,mu_per_min=mu,source_LH_first=info['L_then_H']['state_after_first_manual_kcal_per_min'],source_LH_second=info['L_then_H']['state_after_second_manual_kcal_per_min'],source_LH_peak=str(lh),source_HL_first=info['H_then_L']['state_after_first_manual_kcal_per_min'],source_HL_second=info['H_then_L']['state_after_second_manual_kcal_per_min'],source_HL_peak=str(hl),source_peak_LH_minus_HL=str(gap),counterfactual_LH_first=str(cf['L_then_H']['first']),counterfactual_LH_second=str(cf['L_then_H']['second']),counterfactual_LH_peak=str(cf['L_then_H']['peak']),counterfactual_HL_first=str(cf['H_then_L']['first']),counterfactual_HL_second=str(cf['H_then_L']['second']),counterfactual_HL_peak=str(cf['H_then_L']['peak']),counterfactual_peak_LH_minus_HL=str(cf_gap),source_preference='H_then_L',counterfactual_preference='H_then_L',source_HL_has_down=True,down_required_for_preference=False,analytic_gap=str(closed)))
    write(out/'WP05_S1_PAIR_RESULTS.csv',records);write(out/'WP05_S1_STATE_TRACES.csv',traces)
    gaps=[Decimal(r['source_peak_LH_minus_HL']) for r in records]
    record=dict(status='PASS',parameter_pairs=20,original_schedule_rows_exactly_reproduced=matched_rows,decimal_precision=100,scenario_sha256=digest(ROOT/'artifacts/wp03_scenario_inputs.json'),scenario_schedule_sha256=digest(ROOT/'artifacts/wp03_schedule_evaluations.csv'),existing_claim_map_sha256=digest(claim_map_path),existing_S1_claim_tags=[r['required_claim_tags'] for r in claim_map],evaluator_sha256=digest(ROOT/'scripts/wp03_evaluate_schedules.py'),audit_code_sha256=digest(Path(__file__)),peak_gap_min=str(min(gaps)),peak_gap_max=str(max(gaps)),H_then_L_source_has_down_all_pairs=True,H_then_L_preference_requires_down=False,no_decrease_preserves_peak_values_and_preference_all_pairs=True,magnitude_component='Only frozen synthetic S1 states are audited; no observed ACC state magnitudes are reconstructed.')
    save(out/'verification/S1_audit_checks.json',record)
    text=f'''# WP-05 S1 decision-path audit

This audits the existing frozen two-order S1 scenario only. No original scenario, model definition, or manuscript file was changed. The no-decrease operation below is solely the requested diagnostic counterfactual, not a source-faithful alternative fatigue model or a new scheduling experiment.

## Frozen inputs and exact trace reproduction

E_R={s['E_R_kcal_per_min']}, E_L={s['E_L_kcal_per_min']}, E_H={s['E_H_kcal_per_min']} kcal/min model state; D={s['D_minutes']} minutes. Initial state E_R; objective minimum peak state after either active task. Both orders retain the same two tasks and makespan. All 40 source schedule rows (20 pairs × two orders) exactly reproduce the frozen WP-03 state and peak columns using the unchanged evaluator at Decimal precision 100. Full pair results and step traces are saved in `WP05_S1_PAIR_RESULTS.csv` and `WP05_S1_STATE_TRACES.csv`.

## Mathematical dependency

Let q=exp(-lambda D), r=exp(-mu D). Because E_R<E_L<E_H, the first L and first H are increases:

- L1 = E_L + (E_R-E_L)q.
- H1 = E_H + (E_R-E_H)q.
- L→H second state = E_H + (L1-E_H)q, its peak.
- In all 20 frozen pairs H1>E_L. H→L therefore decreases to E_L+(H1-E_L)r, below H1, and its peak is H1.

Hence peak(L→H) − peak(H→L) = (L1−E_R)q = (E_L−E_R)(1−q)q > 0. It is independent of mu. The peak gap ranges from {min(gaps):.9E} to {max(gaps):.9E} kcal/min model state. Very small formal differences have no established practical threshold or observed worker-benefit interpretation.

The strict peak preference depends on inherited state entering H: prior L elevates H's starting state above E_R, whereas H first starts from E_R. Finite monotone increase toward task-dependent targets and the peak objective preserve this inherited-state difference. The high-to-low source trace contains a downward active-work transition, but the magnitude/rate of that decrease does not determine the peak-order preference. No rest update is involved. Resetting the inherited state algebraically before each task would remove this particular order dependence; no additional reset scenario was simulated.

## Requested diagnostic counterfactual

At each active-work step, compute the original update, then accept max(prior_state, original_update). Every other input and operation is unchanged. In H→L the second state remains at H1 rather than decreasing; in L→H both increases remain unchanged. Both peak values, their gap, and the H→L preference remain **exactly unchanged in all 20 pairs**.

1. Does the preference require a downward active-work transition? **No.** Such a transition occurs in the source H→L trace, but it is not necessary for this peak objective's ordering.
2. Does it remain under the neutral no-decrease diagnostic counterfactual? **Yes, in all 20 pairs, with identical peaks.**

## Behavioral precision of the existing evidence mapping

The existing WP-03 claim map labels S1 broadly ACC. This is coarse relative to the audited mathematical dependency: S1's strict choice depends on quantitative target-dependent increases, inherited state, and the peak criterion; it does not require empirical validity of the downward active-work regime. Conversely, support for positive ordinal UP direction alone does not validate quantitative state magnitudes, path dependence, extremely small peak differences, or a practical scheduling benefit. Regime-level DOWN weakness cannot by itself negate the formal S1 preference, and UP support alone cannot establish its empirical decision validity. Whether the manuscript mapping should be corrected or qualified remains a Controller decision.
'''
    (out/'WP05_S1_DECISION_PATH_AUDIT.md').write_text(text,encoding='utf-8');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
