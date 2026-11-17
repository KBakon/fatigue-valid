# WP-05 frozen targeted diagnostic specification

WP-05 is a post-WP04 targeted diagnostic analysis motivated after inspecting prior results. It is not preregistered, not prespecified before the original study, and not outcome-blind discovery. This document fixes implementation before new WP-05 inferential calculations. The supplied WP-05 request governs scope. No new sensor predictors, thresholds, model calibration, scenario changes or causal claims are authorized.

## Stage 0 and cohort

Verify existing WP-02 Stage-A/B manifests and hashes, WP-04 output manifest/save status and exact shared cohort. Reaggregate original frozen ACC transition evidence into participant/task means and call the authoritative Python random.Random(20260926), 10,000-resample percentile bootstrap. Reproduce task estimates and matched differences for both families to 1e-10 of frozen numeric tables (and 0.000001 of supplied rounded values). Require 37 distinct participants, 222 paired transitions; Composite 32/121, Harnessing 27/101. Save a keys-only cohort projection and SHA-256 for Stage 1. Do not use WP-04 agreement values in WP-05.

## Structural freeze before empirical join

Stage 1 reads only keys-only cohort, its seal, frozen WP-02 model prediction table, prediction manifest and this specification. Require FAM-A direction +1 and structural robust status. Require every FAM-B row parameter-robust, 20 unique (lambda, mu) pairs equal to the original grid, identical direction in all 20, and consistency with frozen predicted_direction. FAM_B_UP is >0, FAM_B_DOWN is <0, FAM_B_TIE is =0. No sign tolerance or threshold. Preserve original prediction IDs and source provenance in an audit table. Record exact counts by task/regime and transition index without interpretation. Save and seal a write-once deterministic regime table, method SHA-256 and script SHA-256 before Stage 2 opens outcomes. Stage 1 has no access to Borg/agreement tables; audit actual file reads on clean rerun.

## Outcomes and estimands

Join only authoritative WP-02 ACC transition-level observed directions and agreements on the exact participant/task/from/to keys. Verify common observed direction and the original scoring: zero if observed or predicted direction ties, +1 if equal, -1 otherwise. Delta=B-A. No imputation or eligibility expansion.

For UP/DOWN by task, compute the within-participant/task mean agreement on transitions in that regime, then mean across eligible participants. Bootstrap 10,000 participant means, original Python random.Random seed 20260926, percentile CI. Classify lower CI>0 as SUPPORTED; upper CI<0 as DIRECTIONALLY_CONTRADICTED; otherwise EVIDENCE_INSUFFICIENT. Report A, B and paired delta with counts; apply the same structure to both-task participant sensitivity. Participants with no transitions in a regime are absent for that regime, not assigned zero. For pooled secondary summaries, average all eligible regime transitions within participant across tasks, then bootstrap participant means; never treat participant/task observations as distinct people.

All multigroup descriptive bootstrap summaries use the same ordered participant-ID draws and carry all transitions/tasks jointly. Each group's conditional ratio recomputes its eligible-participant denominator after resampling; report missing/empty bootstrap counts. For the specifically authoritative primary task/regime CIs, draw directly from the sorted eligible participant IDs for that group with the original bootstrap function, matching the requested original procedure. This is equivalent to carrying each sampled participant's full observations and evaluating that group; it does not make task rows independent. Separate group CIs do not imply a paired difference CI.

Prevalence: within participant/task, down_share=DOWN/eligible FAM-B ACC transitions in the exact shared cohort. Report participant task means/CIs and the Composite-minus-Harnessing matched participant difference with 10,000 original paired-participant bootstrap samples. Denominator includes any UP/DOWN/TIE. Record denominators. Matched sensitivity uses IDs represented in both tasks on the shared cohort.

## Conditioned model

OLS B agreement ~ intercept + DOWN + Composite + DOWN:Composite + transition_index. Harnessing and UP are references; DOWN=1 for downward predicted direction. If a TIE exists, report it explicitly and exclude it from this two-regime model rather than silently classing it as UP. Coefficients: DOWN is the Harnessing DOWN-vs-UP contrast, Composite is the task contrast within UP, interaction is the difference in DOWN-vs-UP contrast between tasks. Also report task contrast within DOWN as Composite+interaction to clarify residual task conditionality. These are descriptive, not causal effects or mediation.

Resample N participant IDs with replacement 10,000 times using Python random.Random(20260926); each selected participant contributes all shared rows across both tasks. Solve OLS using participant-specific XTX/XTy weighted by sampled ID multiplicities; verify against literal repeated blocks. Use percentile 95% CI, count and exclude rank-deficient draws. Equal transition weights define the regression estimand. Report all coefficients and descriptive R². Repeat without transition_index and within both-task IDs. No new explanatory variables or multiplicity-driven selection. The requested targeted tests are reported together without declaring familywise confirmatory significance.

## Exact family contrast

Verify A and B predicted signs match on every UP row. Algebraically, A=+1 and B=+1 on UP implies equal original agreement for every possible observed sign. On DOWN, A=+1 and B=-1 imply B-A=-2*observed_direction (with tied observations scoring zero). Verify rowwise and report participant-level paired delta/CIs by task. Explicitly check TIE rows before asserting DOWN is the only source of family disagreement.

## Magnitude sensitivity availability rule

Inspect frozen prediction artifact schemas and all per-pair entries for actual observed-transition signed state changes or endpoint states. If no such values are stored, declare model-magnitude sensitivity NOT TESTABLE. Do not rerun propagation from model inputs, derive approximate magnitudes from directions/EER, or substitute WP-03 scenario states for observed transitions. If signed states are genuinely stored, compute exact min/max/median signed change and min/median absolute change, and predictor-only tertiles of median absolute change among DOWN transitions (type-7 cutpoints, right-closed bins, ties at cutpoints remain together; record counts). No arbitrary practical threshold. Tertiles are a requested diagnostic, not outcome-derived splits.

## Existing S1 mathematical audit

Verify frozen WP-03 scenario input seal and authoritative code/input hashes. Use the unchanged original `wp03_evaluate_schedules.work_update/evaluate_b` with Decimal precision 100 and exactly the 20 frozen parameter pairs. Verify both order traces and peak states against the saved WP-03 schedule table. Then evaluate only the requested diagnostic counterfactual: after each active-work update, replace any decrease by the prior state, leaving targets, durations, initial state and peak objective unchanged. This no-decrease operation is not a source-faithful alternative model. Save full traces, DOWN presence, both peak differences and preferences for all pairs. Derive the symbolic peak-order relationship to distinguish a behavior present in a schedule from a behavior necessary for its preference. Do not introduce a new scheduling experiment or change any existing scenario/artifact. Assess the behavioral precision of mapping S1 to generic ACC support; leave correction/publication decisions to the Controller.

## Interpretation and verification

Assess all requested patterns without forcing a result. UP support in both tasks, weak/contradicted DOWN in both, differing DOWN prevalence and an uninformative interaction are consistent with a structural regime boundary; task and within-DOWN task contrasts can still qualify that decomposition. A CI spanning zero is not equivalence and a small interaction estimate is not proof of no task role. Do not call a downward active-work state transition physiological recovery.

Report exact regime/index and observed-direction counts. Repeat support within both-task participants and regression without transition index. All uncertainty uses participant blocks; no sensor samples or transitions become independent participants. Clean rerun into a fresh directory, exact deterministic hashes, structural file-access audit, block-bootstrap audit, full existing-file SHA-256 comparison, output manifest and verified-save status complete the WP. Do not edit manuscript or WP-02/03/04 files. Executor is the current Codex GPT-6-based runtime; exact served model/effort metadata are not exposed, and no subagents are used.
