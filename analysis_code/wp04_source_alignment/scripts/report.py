"""Deterministic factual report and one inspection figure from saved results."""
from pathlib import Path
import csv,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'wp04_source_alignment'
def read(name):
    with (OUT/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def main():
    rr=read('WP04_PRIMARY_RESULTS.csv');tasks=read('WP04_TASK_CHARACTERIZATION.csv');means=read('WP04_PARTICIPANT_FEATURE_MEANS.csv');counts=read('verification/stage2_cohort_counts.csv');att=read('WP04_TASK_ATTENUATION.csv')
    s1=json.loads((OUT/'verification/stage1_manifest.json').read_text());s2=json.loads((OUT/'verification/stage2_manifest.json').read_text());s0=json.loads((OUT/'verification/stage0.json').read_text())
    def result(feature='arm_dominance',outcome='delta_agreement',variant='primary',term=None):
        return next(r for r in rr if r['variant']==variant and r['predictor']==feature and r['outcome']==outcome and r['term']==(term or 'z_'+feature))
    def ci(r):return f"{float(r['estimate']):.6f} [{float(r['ci_lower']):.6f}, {float(r['ci_upper']):.6f}]"
    def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'
    lines=['# WP-04 factual result summary','',
    'Executor: Codex, GPT-6-based agent as identified by runtime instructions. Exact served model identifier and reasoning-effort setting are not exposed; no subagents were used. This is an association test of an upper-limb-versus-torso motion-distribution proxy. No Controller or publication-readiness decision is assigned.','',
    '## 1. Baseline reproduction','',
    'PASS. `scripts/stage0.py` checks the existing frozen Stage-A and Stage-B hashes, then reaggregates the authoritative frozen transition agreements. It calls the original `scripts/wp02_validate.py::boot_ci` with 10,000 participant resamples and seed 20260926. Agreement with saved quantities is within 1e-10. Direct source paths/hashes and results are saved in `verification/stage0.json`. No source outcomes or model parameters were redefined.','',
    table(['Endpoint','Contrast','Participants','Estimate [95% CI]'],[[r['endpoint'],r['contrast'],r['n'],ci(r)] for r in s0['results']]),
    '## 2. Frozen feature construction and non-outcome verification','',
    f"All {s1['source_files']} active segment files were inventoried before numerical feature computation; {s1['eligible_segments']} eligible, {s1['excluded_segments']} excluded, no missing synchrony. No kinematic imputation. Mapping follows the authoritative local dataset dictionary (IMU1 right upper arm; 2 right lower arm; 3 left upper arm; 4 left lower arm; 5 ADAM chest), citing Mohapatra et al. Table 3. The selected fields are common Time and all 15 gx/gy/gz_dps_ channels. The inventory is per source file and selected column; nonselected physiology/survey fields are outside the feature projection.", '',
    'Implementation B: M_s = sqrt(mean(gx²+gy²+gz²)), in degrees/s, with the same definition at all five sites. arm_mean = mean(M1,M2,M3,M4); arm_dominance = arm_mean/(arm_mean+M5+epsilon). epsilon is float64 smallest positive normal, 2.2250738585072014e-308 degrees/s. Asymmetry and zero-lag synchrony follow the saved method specification. All samples were finite and all common time sequences strictly increasing under the declared rules. No zero arm/torso or bilateral denominators occurred.','',
    'The Stage-1 script contains no Borg, agreement, WP-02, or support-classification field references and imports only pathlib, csv, hashlib, json, sys, numpy. It uses `numpy.loadtxt(usecols=...)`: mixed CSV bytes necessarily pass through the parser, but only selected numeric fields are returned/evaluated. File SHA-256 reads are provenance-only. It does not open any downstream outcome/prediction/result table. The clean rerun audits actual project-file reads and tests projection invariance after replacing every nonselected cell with a nonnumeric sentinel. These checks demonstrate computational field blindness, not executor ignorance of previously reported baseline findings.','',
    f"Frozen mechanism SHA-256: `{s1['feature_sha256']}`. The table was saved and sealed before Stage 2 was executed. Its hash is checked before and after the outcome join. Exact source hashes, eligibility rows, formulas, mapping, method and script hashes are in `verification/stage1_*` and the sensor inventory. The method specification was saved before feature generation.", '',
    '## 3. Analytic cohort','',
    f"{s2['participants']} distinct participants, {s2['transitions']} exact paired transitions. Both-task sensitivity: {s2['matched_task_participants']} participants, {s2['matched_task_transitions']} transitions. Features come from segment j+1; transition_index is j (1–4). No primary-study exclusions or prediction-robustness eligibility were expanded. Stage 1 inventories all source segments without using outcome eligibility; Stage 2 restricts to the authoritative shared ACC cohort.",'',
    table(['Task','A eligible transitions','B eligible transitions','Shared before feature','Missing-feature exclusions','Shared participants','Shared transitions'],[[r[k] for k in ('task','ACC_A_transitions','ACC_B_transitions','paired_before_feature','missing_feature_exclusions','participants','transitions')] for r in counts]),
    'The exact rows, identifiers, agreement values, proxy values and pooled z scores are in `WP04_PAIRED_TRANSITIONS.csv`. The cohort file records exclusions explicitly; none resulted from kinematic missingness.','',
    '## 4. Task-characterization result','',
    'Participant/task means are the descriptive unit, with participant-cluster intervals for task means and matched-participant bootstrap intervals for task differences. Primary characterization uses next segments on shared transitions. A separate characterization uses all five active segments of those same eligible participant/task combinations; it does not add excluded participants. Neither comparison uses agreement values.','',
    table(['Cohort','Contrast','Participants','Estimate [95% CI]'],[[r['cohort'],r['contrast'],r['participants'],ci(r)] for r in tasks]),
    'Harnessing has **lower**, rather than the hypothesized higher, arm dominance. The matched Composite-minus-Harnessing interval is entirely positive. This fails the prespecified task-direction condition. Participant-level means are saved in `WP04_PARTICIPANT_FEATURE_MEANS.csv`.','',
    '## 5. Primary arm-dominance result','',
    f"OLS: delta_agreement ~ z_arm_dominance + Composite + transition_index, Harnessing reference. Pooled mean = {s2['standardization']['arm_dominance']['mean']:.9f}; pooled population SD = {s2['standardization']['arm_dominance']['population_sd']:.9f}, computed once across all 222 shared transitions and fixed for resampling/sensitivity. Coefficients are agreement-score units per predictor unit (per one pooled SD for z).",'',
    table(['Term','Estimate [95% participant-bootstrap CI]'],[[term,ci(result(term=term))] for term in ('intercept','Composite_minus_Harnessing','transition_index','z_arm_dominance')]),
    f"Descriptive R² = {float(result()['descriptive_R2']):.6f}. The primary point estimate is positive and its interval spans zero; it does not provide directionally informative evidence of relative FAM-B degradation at higher arm dominance. These intervals do not establish equivalence or rule out a smaller negative association.",'',
    'Descriptive task attenuation (Composite-minus-Harnessing; not causal mediation):','',
    table(['Analysis','M0 task','M1 task','Signed change','Magnitude attenuation %'],[[r['variant']]+[f"{float(r[k]):.6f}" for k in ('M0_task','M1_task','signed_change','magnitude_attenuation_percent')] for r in att]),
    '## 6. FAM-A negative control','',
    table(['Outcome','Arm-dominance coefficient [95% participant-bootstrap CI]'],[[o,ci(result(outcome=o))] for o in ('famA_ACC_agreement','famB_ACC_agreement')]),
    'FAM-A shows no directionally informative general degradation on this proxy. This control alone cannot rescue the mechanism: the hypothesized task direction and relative FAM-B association both fail. FAM-B-only results are descriptive.','',
    '## 7. Secondary results','',
    'Both prespecified features were testable on all 222 shared transitions: asymmetry uses the same five-site RMS definition; synchrony uses the right/left upper-arm magnitude time series already aligned to common Time, Pearson correlation at zero lag, no lag search. No features were combined or selected after outcome inspection. The following raw percentile intervals and descriptive bootstrap sign-tail p summaries are reported. Holm correction is across the two secondary predictors separately within each outcome family; it does not affect the primary test.','',
    table(['Feature','Outcome','Coefficient [95% CI]','Raw sign-tail p','Holm p'],[[f,o,ci(result(f,o)),f"{float(result(f,o)['bootstrap_sign_tail_p']):.6f}",f"{float(result(f,o)['holm_p']):.6f}"] for f in ('bilateral_asymmetry','bilateral_synchrony') for o in ('delta_agreement','famA_ACC_agreement','famB_ACC_agreement')]),
    'Neither secondary relative-agreement interval is directionally informative. Sign-tail summaries are not exact null-randomization p-values.','',
    '## 8. Required robustness checks','',
    'All reported regression intervals use 10,000 participant-ID resamples (seed 20260926); each ID carries all eligible transitions and both task observations jointly. Cluster multiplicities weight per-participant XTX/XTY sufficient statistics. No transition or sensor sample is treated as an independent participant. All resamples were full rank. A separate check compares this algorithm with literal repeated participant blocks for 20 draws.','',
    table(['Sensitivity','Feature','Delta coefficient [95% CI]','A control coefficient [95% CI]'],[[v,f,ci(result(f,variant=v)),ci(result(f,'famA_ACC_agreement',v))] for v in ('matched_tasks','omit_transition_index') for f in ('arm_dominance','bilateral_asymmetry','bilateral_synchrony')]),
    'The primary conclusion does not change under the matched-task restriction or omission of transition index: no directionally informative negative relative arm-dominance association. The pooled scales remain fixed. Exact tie counts on the shared transitions:','',
    table(['Task','A agreement=0','B agreement=0','A observed ties','B observed ties','A prediction ties','B prediction ties'],[[r[k] for k in ('task','famA_agreement_zero','famB_agreement_zero','famA_observed_ties','famB_observed_ties','famA_prediction_ties','famB_prediction_ties')] for r in counts]),
    'Clean rerun commands, file-access audit, deterministic hashes, numerical bootstrap checks, and existing-file integrity results are saved under `verification/`. The project root has no .git; a full SHA-256 snapshot replaces an unavailable root Git diff. Existing nested repository metadata is not modified.','',
    '## 9. What the data support','',
    'The tasks differ on this frozen motion-distribution proxy, with higher Composite arm dominance. The present proxy does not account for the hypothesized FAM-B-specific task failure in the prespecified direction. The empirical WP-04 pattern fails two necessary compatibility conditions: expected task direction and negative directionally informative relative-agreement association. No comparable directionally informative general FAM-A degradation was found. The small descriptive task-coefficient attenuation does not establish an explanatory mechanism.','',
    '## 10. What the data do NOT support','',
    'These results do not support the prespecified proxy-based source-domain-alignment explanation. They do not prove that source-domain mismatch is absent, demonstrate predictor equivalence, measure whole-body involvement, diagnose localized muscular fatigue, quantify force or physiological load, establish causality or mediation, or validate a new fatigue predictor. No scheduling experiment or model calibration to Borg was performed.','',
    '## 11. Unresolved technical/scientific limitations','',
    'Five locations cover arms and chest, with no lower-limb measurement. A ratio of angular motion cannot measure whole-body manual loading, static contraction, external force, or localized fatigue. Source processing includes filtering and resampling at nominal 500 ms; high-frequency motion and original acquisition defects cannot be recovered. Anatomical mapping relies on the frozen repository dictionary and its Table-3 attribution; no per-session raw sensor-placement audit or large raw archive reconstruction was undertaken. All 372 source segments passed the declared numerical checks, but finite values do not establish sensor calibration or measurement validity. The source helper’s derived window RMS/velocity features were not reused.','',
    'The shared cohort is smaller and selected by both existing model-family eligibility rules; these results generalize only within that cohort. Stage-1 eligibility is deliberately conservative for missing/nonfinite samples and was fixed before outcome joining. Regression weights transitions equally, while uncertainty resamples participants; varying eligible-transition counts can affect the estimand. Task characterization weights participant/task means equally, so it need not equal a regression contrast. Agreement is discrete with many ties; OLS and bootstrap quantify descriptive directional association, not latent fatigue magnitude. Bootstrap intervals remain finite-sample approximations. No causal inference, null equivalence claim, or Controller decision follows. Exact served model and effort metadata are unavailable.','']
    (OUT/'WP04_RESULT_SUMMARY.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'figures').mkdir(exist_ok=True)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    a=axs[0];pp=[r for r in means if r['cohort']=='shared_next_active_segments']
    ids=sorted({r['participant_id'] for r in pp})
    for p in ids:
        d={r['task']:float(r['mean_arm_dominance']) for r in pp if r['participant_id']==p}
        if len(d)==2:a.plot([0,1],[d['Composite'],d['Harnessing']],color='#c8c8c8',lw=.7,zorder=1)
    for j,t in enumerate(('Composite','Harnessing')):
        yy=[float(r['mean_arm_dominance']) for r in pp if r['task']==t]
        a.scatter(np.full(len(yy),j),yy,s=17,alpha=.65,color=('#3174a1','#cb7c2d')[j],zorder=2)
        r=next(r for r in tasks if r['cohort']=='shared_next_active_segments' and r['contrast']==t);est=float(r['estimate'])
        a.errorbar(j+.12,est,yerr=[[est-float(r['ci_lower'])],[float(r['ci_upper'])-est]],fmt='D',color='black',capsize=4,zorder=3)
    a.set(xticks=[0,1],xticklabels=['Composite','Harnessing'],ylabel='Participant mean arm dominance',title='Task characterization: shared transitions',xlim=(-.35,1.35))
    a.text(.02,.02,'Lines: matched participants\nBlack: task mean and participant-bootstrap 95% CI',transform=a.transAxes,fontsize=8)
    a=axs[1]
    for j,(o,label) in enumerate((('delta_agreement','B − A (primary)'),('famA_ACC_agreement','FAM-A control'),('famB_ACC_agreement','FAM-B descriptive'))):
        r=result(outcome=o);est=float(r['estimate']);a.errorbar(est,j,xerr=[[est-float(r['ci_lower'])],[float(r['ci_upper'])-est]],fmt='o',color='#3174a1',capsize=5)
    a.axvline(0,color='gray',ls='--',lw=1);a.set(yticks=[0,1,2],yticklabels=['B − A (primary)','FAM-A control','FAM-B descriptive'],xlabel='Agreement change per pooled SD of arm dominance',title='Adjusted coefficients: participant-bootstrap 95% CI');a.invert_yaxis()
    fig.savefig(OUT/'figures/WP04_mechanism.png',dpi=160,metadata={'Software':'WP04 saved report.py'});plt.close(fig)
    print('Saved factual summary and one inspection figure.')
if __name__=='__main__':main()
