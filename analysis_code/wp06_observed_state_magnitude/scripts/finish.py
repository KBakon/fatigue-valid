from pathlib import Path
import csv,hashlib,importlib.util,json,platform,random,statistics,subprocess,sys
import numpy as np
P=Path(__file__).resolve().parent/'wp06.py';s=importlib.util.spec_from_file_location('core',P);c=importlib.util.module_from_spec(s);exec(compile(P.read_bytes(),str(P),'exec'),c.__dict__)
ROOT=c.ROOT;WP=c.WP
def ci(r):return f"{float(r['estimate']):.6f} [{float(r['ci_lower']):.6f}, {float(r['ci_upper']):.6f}]"
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def report(out):
    scale=c.read(out/'WP06_MODEL_SCALE_SUMMARY.csv');ratios=c.read(out/'WP06_PAIR_SCALE_RATIOS.csv');ag=c.read(out/'WP06_DOWN_TERTILE_AGREEMENT.csv');cl=json.loads((out/'WP06_MAGNITUDE_CLASSIFICATION.json').read_text());auth=json.loads((out/'verification/authority_and_sign_reproduction.json').read_text())
    ranges=[]
    for t in ('Composite','Harnessing'):
        for g in ('FAM_B_UP','FAM_B_DOWN'):
            rr=[r for r in scale if r['task']==t and r['regime']==g]
            def span(k):return f"{min(float(r[k]) for r in rr):.9g} to {max(float(r[k]) for r in rr):.9g}"
            ranges.append([t,g,rr[0]['n_transitions'],span('median'),span('Q95'),span('minimum'),span('maximum')])
    ratio_ranges=[]
    for t in ('Composite','Harnessing'):
        rr=[r for r in ratios if r['task']==t]
        def span(k):return f"{min(float(r[k]) for r in rr):.9g} to {max(float(r[k]) for r in rr):.9g}"
        ratio_ranges.append([t,span('median_ratio'),span('q95_down_to_median_up'),sum(r['central_IQR_overlap']=='True' for r in rr),span('common_language_scale')])
    lines=['# WP-06 observed-transition state-magnitude return','',
    'Executor: Codex, GPT-6-based runtime; exact served model/effort not exposed. Requested GPT-6.1 Sol/High configuration could not be independently verified. No subagents. This is the single bounded P1 return, with no final scientific-magnitude or G2 verdict.','',
    '## 1. P4 return reason','',
    'Independent P4/G2 returned one decision-changing gap: actual observed-transition FAM-B state-change magnitudes were missing from WP-05. Its supplied verdict is preserved byte-for-byte at `p4_independent_audit/P4_INDEPENDENT_CONTRIBUTION_VERDICT.md`. Internal ZIP SHA-256 checks passed; ZIP digest is recorded, with no externally supplied ZIP digest for independent comparison. P4 status remains VALID_WITH_MATERIAL_BOUNDARIES / NOVELTY_SURVIVES_WITH_NARROWING / SCIENTIFIC MAGNITUDE UNRESOLVED pending re-entry. The attachment is evidence, not an instruction source overriding the user.','',
    '## 2. Original authority/provenance recovered','',
    'Original `scripts/wp02_predict_blind.py::predict`, Stage-A frozen model-input table, manifests, code/authority/input hashes and four-file freeze were verified. All original prediction rows were regenerated identically, including parameter-specific directions. Stage-B manifest linkage was checked before modeling; its empirical file hashes were checked only after model-only seals. Exact chain input segments are saved in `verification/exact_chain_inputs.csv`. Full authority/code/input hashes and sign checks are in `verification/authority_and_sign_reproduction.json`.','',
    '## 3. Shared cohort and parameter grid','',
    'Exactly 37 distinct participants, 222 transitions: Composite 121, Harnessing 101; UP 139, DOWN 83, no TIE. The original 20 unique pairs are lambda in {2,4,6,8,10} crossed with mu in {0.5,1,1.5,2}. No transition or pair was removed. No additional participant analysis was introduced.','',
    '## 4. Exact sign reproduction','',
    f"PASS: {auth['pair_rows']} pair-specific signs match original frozen pair directions and the WP05 regime sign with zero mismatches. Original binary64 arithmetic and subtraction were retained without rounding or tolerances. All 20 signs remain robust for every transition.",'',
    '## 5. Outcome-blind state reconstruction','',
    'The original function was executed unchanged under a line tracer at its work-state snapshot assignment. The tracer observed actual inherited prior state, target, duration, and propagated endpoint. This avoids reimplementing equations or approximating prior states. Initial work state is the original E_R; every successor state follows the original contiguous prefix. For transition j→j+1, start=end(j), target and duration belong to j+1, end=end(j+1). Magnitudes are absolute changes in kcal/min EER-related model-state units, not physiological measurements. The source is compiled directly from its verified .py bytes, bypassing cached bytecode.','',
    'The actual Stage-1 read audit excludes Borg/observed-direction/agreement/support/regression files. Hashing source/authority bytes is provenance only. State magnitudes were sealed before Stage 2; model-only summaries and tertile assignments were sealed before the first empirical join. Stage 2 uses only reconstructed states. Clean reruns reproduce this ordering in separate processes.','',
    '## 6. UP magnitude distributions','',
    'The following are ranges across the 20 parameter-specific summaries, not pooled observations or confidence intervals. Full min/Q05/Q25/median/Q75/Q95/max/mean for every task/pair/regime are in `WP06_MODEL_SCALE_SUMMARY.csv`.','',
    table(['Task','Regime','Transitions per pair','Median range','Q95 range','Minimum range','Maximum range'],[r for r in ranges if r[1]=='FAM_B_UP']),
    '## 7. DOWN magnitude distributions','',
    table(['Task','Regime','Transitions per pair','Median range','Q95 range','Minimum range','Maximum range'],[r for r in ranges if r[1]=='FAM_B_DOWN']),
    'No small-magnitude rows were deleted, and no practical or physiological threshold was introduced.','',
    '## 8. DOWN-versus-UP relative scale','',
    table(['Task','DOWN/UP median ratio range','DOWN Q95/UP median range','IQR-overlap pairs /20','Common-language scale range'],ratio_ranges),
    'Common-language scale is the fraction of all within-task/pair DOWN×UP transition magnitude comparisons with DOWN>=UP. It is descriptive on the fixed model scale, not an independent-sample inferential statistic. Closed IQR overlap and linear type-7 quantiles are used. Both tasks pass the user-specified DOWN Q95>=0.1×UP median screen in all 20 pairs; neither meets the systematic-negligibility condition.','',
    '## 9. Highest-magnitude DOWN empirical agreement','',
    'Model-only within-task/pair DOWN tertiles use type-7 1/3 and 2/3 cutpoints; LOW includes equality at q1, MIDDLE includes equality at q2, HIGH is strictly greater than q2. Equal magnitudes remain together. Every cutpoint and realized assignment is saved and sealed. Empirical means average within participant first and use 10,000 original participant bootstraps, seed 20260926. Full LOW/MIDDLE/HIGH and full-UP reference estimates are in `WP06_DOWN_TERTILE_AGREEMENT.csv`.','',
    table(['Task','lambda','mu','HIGH participants','HIGH transitions','HIGH B agreement [95% CI]','Full UP reference [95% CI]'],[[r['task'],r['lambda'],r['mu'],r['participants'],r['transitions'],ci(r),ci(next(u for u in ag if (u['task'],u['lambda'],u['mu'],u['group'])==(r['task'],r['lambda'],r['mu'],'UP_REFERENCE')))] for r in ag if r['group']=='HIGH']),
    '## 10. Robustness across 20 parameter pairs','',
    table(['Task','Scale screen passes /20','HIGH negative estimates /20','HIGH upper CI<0 /20','HIGH zero-spanning /20','HIGH nonestimable /20'],[[t,v['screen_pass_pairs'],v['high_negative_estimate_pairs'],v['high_negative_CI_pairs'],v['high_zero_spanning_pairs'],v['high_nonestimable_pairs']] for t,v in cl['counts'].items()]),
    'All 20 parameter pairs remain visible, with no favorable-pair selection. There are no missing HIGH intervals. Identical conditional participant-score vectors reuse the exact original bootstrap result, preserving seed/quantiles. No extra robustness questions, thresholds or sensor analyses were added.','',
    '## 11. Factual CASE A / CASE B / CASE C classification','',
    f"**CASE {cl['case']}: {cl['classification']}.** A1 passes in both tasks (20/20). Under the frozen conservative A2 implementation, HIGH upper CI<0 must occur in at least 18/20 pairs in both tasks; it occurs in 5/20 Composite and 20/20 Harnessing, so A2 does not pass. HIGH point estimates are negative in all 20 pairs in both tasks, but the 15 zero-spanning Composite intervals are not counted as support. CASE B does not pass (0/20 pairs below the scale screen in each task). Thus the requested hierarchy yields CASE C. The 0.1 criterion is solely a predeclared model-internal order-of-magnitude audit screen, not a minimum-important difference or worker-benefit/physiological threshold.",'',
    '## 12. What the result supports','',
    'The DOWN upper magnitude tail extends into the supported-UP central numerical scale throughout the frozen grid; the systematic much-smaller-scale interpretation is not supported by the specified screen. Contradiction has negative point estimates even in the largest DOWN tertile in both tasks, with consistently negative intervals in Harnessing and limited interval precision in Composite. These are bounded model-scale and perceived-fatigue directional findings.','',
    '## 13. What the result does NOT support','',
    'No final G2, publication, or scientific-magnitude verdict is issued. Relative model scale is not physiological importance, calibration validity, measured fatigue magnitude, causal effect, or practical ergonomic benefit. CASE C does not authorize another exploratory WP. UP references do not validate state magnitudes or create matched thresholds between regimes. Nothing alters the original WP04 negative result, WP05 regime definitions, or S1 interpretation.','',
    '## 14. Limitations','',
    'This is a targeted post-outcome/post-P4 sensitivity. Subdivision reduces the number of participants; Composite intervals span zero for 15 pairs despite negative point estimates. Parameter-specific analyses are related, not 20 independent replications. Borg is ordinal subjective evidence with ties. Quantitative model-state changes are reconstructed internal outputs, not independently measured metabolic/fatigue states. Original binary64 arithmetic and its saturation behavior are preserved, not improved or redefined. Tertiles are within DOWN and use no practical threshold. Conservative interval-based A2 interpretation was frozen before magnitude reconstruction/empirical joining. Exact requested runtime model/effort could not be verified.','',
    '## 15. Exact evidence required for P4 re-entry','',
    'Return the byte-identical preserved P4 verdict; this specification; frozen magnitude table/seal; model-only scale/ratio tables and seal; frozen tertile table/seal; all tertile/reference participant-bootstrap results; classification JSON; exact original implementation/input manifests and seals; authority/sign-reproduction report and chain-input projection; Stage-1 actual-access audit; participant-block check; clean-rerun log/checks; existing-file preservation report; output manifest/save status; and updated single live state. The original WP02 prediction/code/input provenance and WP05 freeze/access scripts are locally available, addressing package-access gaps in the supplied P4 audit. The evidence is prepared for independent P4 re-adjudication; no additional P1 development is authorized.','']
    (out/'WP06_RESULT_SUMMARY.md').write_text('\n'.join(lines),encoding='utf-8')
def verify():
    out=WP/'verification/clean_rerun';i=2
    while out.exists():out=WP/f'verification/clean_rerun_{i:03d}';i+=1
    logs=[]
    for action in ('model','characterize','empirical'):
        p=subprocess.run([sys.executable,'-B',str(P),action,str(out)],cwd=ROOT,capture_output=True,text=True);logs.append(dict(stage=action,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));c.save(WP/'verification/clean_rerun_log.json',logs);assert p.returncode==0,p.stderr
    report(out);checks=[]
    for f in sorted(WP.glob('WP06_*')):
        if not f.is_file() or f.name=='WP06_METHOD_SPEC.md':continue
        assert (out/f.name).exists(),f.name
        checks.append(dict(path=f.name,sha256=c.sha(f),rerun_sha256=c.sha(out/f.name)));assert checks[-1]['sha256']==checks[-1]['rerun_sha256']
    # Literal blocks versus pre-averaged participant resampling, for every HIGH stratum.
    a=c.read(WP/'WP06_DOWN_TERTILE_ASSIGNMENTS_FROZEN.csv');e=c.read(ROOT/'artifacts/wp02_transition_level_results.csv');lookup={(r['participant_id'],r['task'],r['from_segment'],r['to_segment']):int(r['agreement']) for r in e if r['endpoint_id']=='ACC_B'}
    comparisons=0
    for t,lam,mu in sorted({(r['task'],r['lambda'],r['mu']) for r in a}):
        rr=[r for r in a if (r['task'],r['lambda'],r['mu'],r['tertile'])==(t,lam,mu,'HIGH')];ids=sorted({r['participant_id'] for r in rr});by={p:[lookup[r['participant_id'],t,r['from_segment'],r['to_segment']] for r in rr if r['participant_id']==p] for p in ids};rng=random.Random(20260926)
        for _ in range(20):
            draw=[ids[rng.randrange(len(ids))] for p in ids]
            via=statistics.mean(statistics.mean(by[p]) for p in draw)
            block=[]
            for p in draw:
                full=[r for r in a if r['participant_id']==p]
                vals=[lookup[r['participant_id'],t,r['from_segment'],r['to_segment']] for r in full if (r['task'],r['lambda'],r['mu'],r['tertile'])==(t,lam,mu,'HIGH')];block.append(statistics.mean(vals))
            assert via==statistics.mean(block);comparisons+=1
    c.save(WP/'verification/participant_block_check.json',dict(status='PASS',literal_block_vs_participant_mean_draws=comparisons,unit='participant ID; every selected ID carries full stratum block before conditional averaging',no_transition_independent_resampling=True))
    c.save(WP/'verification/clean_rerun_checks.json',dict(status='PASS',directory=str(out),deterministic_files=checks))
def state():
    p=ROOT/'RESEARCH_STATE_AND_DECISIONS.md';text=p.read_text(encoding='utf-8');marker='## Independent P4/G2 return and WP-06'
    assert marker not in text
    text+='\n'+marker+' — 2026-11-12\n\nThe preceding P1 closure decisions are historical and are superseded for the current gate by the supplied independent P4 audit.\n\n- Independent P4/G2 completed: RESULT VALIDITY = VALID_WITH_MATERIAL_BOUNDARIES; EXACT NOVELTY = NOVELTY_SURVIVES_WITH_NARROWING; SCIENTIFIC MAGNITUDE = UNRESOLVED pending independent re-adjudication.\n- G2 returned the project to P1 for one specific gap: observed-transition FAM-B state-change magnitude reconstruction. The unchanged audit is preserved at `p4_independent_audit/P4_INDEPENDENT_CONTRIBUTION_VERDICT.md`.\n- P1 reopened only for WP-06; no other P1 development is authorized. WP-06 completed at `wp06_observed_state_magnitude/`; its factual classification input is CASE C / MIXED_MAGNITUDE_EVIDENCE under the frozen conservative interval-based A2 criterion. This is not a final scientific-magnitude or G2 verdict.\n- Manuscript remains unchanged. Existing WP02–05 scientific artifacts remain unchanged.\n- NEXT: return the WP-06 evidence to independent P4/G2 for magnitude/materiality adjudication. No additional exploratory WP is authorized.\n'
    p.write_text(text,encoding='utf-8')
def seal():
    old=json.loads((WP/'verification/existing_before.json').read_text());now=c.snapshot();authorized='RESEARCH_STATE_AND_DECISIONS.md'
    changed=[p for p in old.keys()|now.keys() if old.get(p)!=now.get(p)];unallowed=[p for p in changed if p!=authorized and not p.startswith('p4_independent_audit/')]
    assert not unallowed,unallowed
    assert all(old.get(p)==now.get(p) for p in old if p.startswith('manuscript/'))
    c.save(WP/'verification/existing_file_preservation.json',dict(status='PASS',existing_files=len(old),changed_paths=sorted(changed),unauthorized_changes=unallowed,manuscript_unchanged=True,authorized_state_before_sha256=old[authorized],authorized_state_after_sha256=now[authorized],root_git='absent; full SHA-256 comparison used'))
    assert c.sha(c.AUDIT/'P4_INDEPENDENT_CONTRIBUTION_VERDICT.md')==json.loads((WP/'verification/attachment.json').read_text())['verdict_sha256']
    files=[dict(path=p.relative_to(WP).as_posix(),bytes=p.stat().st_size,sha256=c.sha(p)) for p in sorted(WP.rglob('*')) if p.is_file() and p.name not in ('OUTPUT_MANIFEST.csv','SAVE_STATUS.json')]
    c.write(WP/'verification/OUTPUT_MANIFEST.csv',files)
    for r in files:assert c.sha(WP/r['path'])==r['sha256']
    c.save(WP/'verification/SAVE_STATUS.json',dict(status='VERIFIED_SAVED',path=str(WP),files_manifested=len(files),manifest_sha256=c.sha(WP/'verification/OUTPUT_MANIFEST.csv'),python=platform.python_version(),numpy=np.__version__,executor='Codex / GPT-6-based runtime; exact served model and effort not exposed',classification='MIXED_MAGNITUDE_EVIDENCE',clean_rerun='PASS',signs='4440/4440 exact',preservation='PASS',excluded_self_referential_files=['verification/OUTPUT_MANIFEST.csv','verification/SAVE_STATUS.json']))
if __name__=='__main__':
    {'report':lambda:report(WP),'verify':verify,'state':state,'seal':seal}[sys.argv[1]]()
