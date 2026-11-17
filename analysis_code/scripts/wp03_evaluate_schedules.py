"""Exact enumeration of the two frozen WP-03 feasible schedule sets."""
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
import argparse
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
GRID = tuple((lam, mu) for lam in (2, 4, 6, 8, 10) for mu in (0.5, 1, 1.5, 2))
FEASIBLE = {
    "S1": {"S1_A": ("L", "H"), "S1_B": ("H", "L")},
    "S2": {"S2_A": ("H1", "Rbot", "H2"), "S2_B": ("H1", "H2", "Rbot")},
}
TASKS = ("Composite", "Harnessing")
EVAL_FIELDS = ("model_family", "scenario_id", "schedule_id", "production_sequence", "lambda_per_min",
               "mu_per_min", "state_after_first_manual_kcal_per_min", "state_after_second_manual_kcal_per_min",
               "pre_h2_state_kcal_per_min", "peak_manual_state_kcal_per_min", "objective_value",
               "objective_unit", "parameter_pair_choice", "model_semantic_choice")
MAP_FIELDS = ("model_family", "scenario_id", "task_context", "schedule_a", "schedule_b",
              "model_semantic_choice", "parameter_robust", "required_claim_tags", "wp02_support_status",
              "defensible_choice_after_restriction", "consequence_class", "interpretation_limit")
CONSEQUENCES = {"PRESERVED", "NARROWED_TO_NO_UNIQUE_CHOICE", "CONDITIONAL_BY_TASK",
                "MODEL_DISAGREEMENT", "NOT_TESTABLE"}

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_frozen(path):
    sidecar = path.with_suffix(".sha256")
    expected = sidecar.read_text(encoding="utf-8").strip()
    if expected != f"{digest(path)}  {path.name}":
        raise ValueError("WP-03 scenario input freeze mismatch")
    scenario = json.loads(path.read_text(encoding="utf-8"))
    if digest(ROOT / scenario["source_input_file"]) != scenario["source_input_sha256"]:
        raise ValueError("Stage-A input file changed")
    if digest(ART / "wp02_stage_a_manifest.json") != scenario["stage_a_manifest_sha256"]:
        raise ValueError("Stage-A manifest changed")
    if digest(ART / "wp02_stage_a_freeze.sha256") != scenario["stage_a_freeze_sha256"]:
        raise ValueError("Stage-A freeze changed")
    for name, sha in scenario["authority_file_hashes_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Authority changed after scenario freeze: {name}")
    for name, sha in scenario["code_file_hashes_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Scenario-builder code changed after freeze: {name}")
    if scenario["R_minutes"] != 5.0 or scenario["E_R_kcal_per_min"] != 1.86:
        raise ValueError("Frozen rest inputs differ from authority")
    return scenario

def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def work_update(state, target, duration, lam, mu):
    rate = lam if target >= state else mu
    return target + (state - target) * (-rate * duration).exp()

def rest_update(state, duration, mu, rest_reference):
    return max(rest_reference, state * (-mu * duration).exp())

def evaluate_b(sequence, scenario, lam, mu):
    er = Decimal(str(scenario["E_R_kcal_per_min"]))
    el = Decimal(str(scenario["E_L_kcal_per_min"]))
    eh = Decimal(str(scenario["E_H_kcal_per_min"]))
    duration = Decimal(str(scenario["D_minutes"]))
    rest_duration = Decimal(str(scenario["R_minutes"]))
    rate_lam, rate_mu = Decimal(lam), Decimal(str(mu))
    state = er
    after_manual = []
    pre_h2 = None
    for element in sequence:
        if element == "Rbot":
            state = rest_update(state, rest_duration, rate_mu, er)
        else:
            if element == "H2":
                pre_h2 = state
            target = el if element == "L" else eh
            state = work_update(state, target, duration, rate_lam, rate_mu)
            after_manual.append(state)
    return {
        "state_after_first_manual_kcal_per_min": str(after_manual[0]),
        "state_after_second_manual_kcal_per_min": str(after_manual[1]),
        "pre_h2_state_kcal_per_min": str(pre_h2) if pre_h2 is not None else "",
        "peak_manual_state_kcal_per_min": str(max(after_manual)),
        "objective": pre_h2 if pre_h2 is not None else max(after_manual),
    }

def load_support():
    path = ART / "wp02_behavior_evidence_table.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        allowed = ("model_family", "claim_tag", "task", "status", "interpretation_limit")
        indices = [header.index(name) for name in allowed]
        rows = [dict(zip(allowed, (raw[index] for index in indices))) for raw in reader]
    support = {(row["model_family"], row["claim_tag"], row["task"]): row for row in rows}
    required = {(family, claim, task) for family in ("FAM-A", "FAM-B")
                for claim in ("ACC", "REC") for task in TASKS}
    if not required.issubset(support):
        raise ValueError("WP-02 support map incomplete")
    for key in required:
        row = support[key]
        expected = ("NOT_SUPPORTED" if key == ("FAM-B", "ACC", "Harnessing")
                    else "SUPPORTED_FOR_CLAIM")
        if row["status"] != expected:
            raise ValueError(f"WP-02 status differs from Controller authority: {key}")
        if expected == "NOT_SUPPORTED" and "EVIDENCE_INSUFFICIENT" not in row["interpretation_limit"]:
            raise ValueError("Harnessing ACC_B is not explicitly evidence-insufficient")
    return support

def report_text(scenario, semantic, mapping, numeric, scenario_sha):
    def option(family, sid, task):
        return next(row for row in mapping if row["model_family"] == family and
                    row["scenario_id"] == sid and row["task_context"] == task)
    a_s1_c, a_s1_h = option("FAM-A", "S1", "Composite"), option("FAM-A", "S1", "Harnessing")
    b_s1_c, b_s1_h = option("FAM-B", "S1", "Composite"), option("FAM-B", "S1", "Harnessing")
    a_s2_c, a_s2_h = option("FAM-A", "S2", "Composite"), option("FAM-A", "S2", "Harnessing")
    b_s2_c, b_s2_h = option("FAM-B", "S2", "Composite"), option("FAM-B", "S2", "Harnessing")
    s1_diffs = numeric["S1_differences"]
    s2_diffs = numeric["S2_differences"]
    return f"""# FATIGUE-VALID — WP-03 scheduling consequence report

**Status:** COMPLETED — bounded scheduling consequence adjudicated.  
**Scenario freeze:** `wp03_scenario_inputs.json` SHA-256 `{scenario_sha}`.  
**Scope:** Two predeclared schedule pairs under one exact exhaustive enumerator; no scheduling benchmark.

## Frozen representative inputs

From {scenario['eligible_work_segment_count']} primary-eligible Stage-A work segments ({scenario['eligible_participant_count']} participants), using the frozen Keytel equation and pooled type-7 percentiles:

| Input | Value |
|---|---:|
| E_L, 25th percentile work EER | {scenario['E_L_kcal_per_min']:.12g} kcal/min |
| E_H, 75th percentile work EER | {scenario['E_H_kcal_per_min']:.12g} kcal/min |
| D, median work duration | {scenario['D_minutes']:.12g} min |
| R, robot-only worker rest | {scenario['R_minutes']:.12g} min |
| E_R, source resting reference | {scenario['E_R_kcal_per_min']:.12g} kcal/min |

The builder read only the exact frozen Stage-A model-input table. It checked the Stage-A hashes and wrote and sealed these values before schedule evaluation. It did not read Borg, WP-02 agreement scores or schedule outcomes when choosing inputs.

## Common scheduler and scenario S1 — task order

The enumerator evaluated exactly `S1_A = L -> H` and `S1_B = H -> L`. Each has one low-EER and one high-EER task of duration D, so both have makespan `2D = {2*scenario['D_minutes']:.12g}` minutes. The criterion was minimum peak state after either manual task.

FAM-A gives a **tie / no unique task-order choice** in both contexts. Its frozen structural accumulation has no task-specific load or numeric rate. FAM-B evaluated both orders for all 20 frozen parameter pairs. Its formal model-semantic choice was **{semantic['FAM-B']['S1']}** in all pairs. The peak difference (`S1_A` minus `S1_B`) ranged from {min(s1_diffs):.6E} to {max(s1_diffs):.6E} kcal/min over the envelope. This is a mathematical ordering under the source equations, not an estimated practical worker benefit; the smallest differences are extremely small and no equivalence or action threshold was defined.

| Family | Composite after WP-02 filter | Harnessing after WP-02 filter | Consequence |
|---|---|---|---|
| FAM-A | {a_s1_c['defensible_choice_after_restriction']} | {a_s1_h['defensible_choice_after_restriction']} | No unique task-order choice was available before or after filtering. |
| FAM-B | {b_s1_c['defensible_choice_after_restriction']} | {b_s1_h['defensible_choice_after_restriction']} | Composite: {b_s1_c['consequence_class']}; Harnessing: {b_s1_h['consequence_class']}; across tasks: CONDITIONAL_BY_TASK. |

Harnessing ACC_B remains **NOT_SUPPORTED — EVIDENCE INSUFFICIENT**, which narrows a formal FAM-B preference to no defensible unique choice from current evidence. This is not a falsification. In Composite, FAM-A is indifferent while FAM-B has a unique formal preference; there are different defensible choice sets, not opposing unique choices. After filtering in Harnessing, both families leave both task orders admissible.

## Scenario S2 — rest placement

The enumerator evaluated exactly `S2_A = H1 -> Rbot -> H2` and `S2_B = H1 -> H2 -> Rbot`. Each contains H1, H2 and the same five-minute robot-only operation. Both have makespan `2D+R = {2*scenario['D_minutes']+scenario['R_minutes']:.12g}` minutes. The criterion was fatigue state immediately before H2 starts.

FAM-A supplies the qualitative preference **S2_A**, using only positive recovery. It supplies no numeric state or rate. FAM-B's source-floor rest update gave **{semantic['FAM-B']['S2']}** in all 20 pairs. The modeled pre-H2 difference (`S2_B` minus `S2_A`) ranged from {min(s2_diffs):.6E} to {max(s2_diffs):.6E} kcal/min. These are model states, not measured worker fatigue or an intervention effect.

| Family | Composite after WP-02 filter | Harnessing after WP-02 filter | Consequence |
|---|---|---|---|
| FAM-A | {a_s2_c['defensible_choice_after_restriction']} | {a_s2_h['defensible_choice_after_restriction']} | PRESERVED in both contexts. |
| FAM-B | {b_s2_c['defensible_choice_after_restriction']} | {b_s2_h['defensible_choice_after_restriction']} | PRESERVED in both contexts. |

Both families imply the same pairwise rest-placement preference, and the required REC behavior is supported in both WP-02 task contexts. This does not establish an individual recovery time constant or real-world causal benefit.

## Claim boundary and reproducibility

The two scenarios complete the bounded scheduling-consequence part of RQ1: empirical support preserves the rest-placement choice, while it makes the FAM-B task-order choice task-conditional and removes its unique defensible status in Harnessing. FAM-A has no unique S1 task-order choice because its authorized primary semantics are structural and task independent. No model-wide preference is inferred.

`wp03_schedule_evaluations.csv` contains each enumerated schedule and every FAM-B parameter pair; `wp03_before_after_claim_map.csv` contains the eight family × scenario × task-context decisions plus an across-task FAM-B S1 conditionality row. The verifier rebuilds all four required artifacts in a clean directory and compares hashes.

**No Borg value was read by WP-03. No global model ranking, numeric FAM-A magnitude, new parameter fitting, best-pair selection or optimizer-performance claim was produced.**
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-inputs", type=Path, default=ART / "wp03_scenario_inputs.json")
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    scenario = load_frozen(args.scenario_inputs)
    support = load_support()
    evaluations = []
    pair_choices = defaultdict(list)
    differences = {"S1_differences": [], "S2_differences": []}
    with localcontext() as context:
        context.prec = 100
        for sid, schedules in FEASIBLE.items():
            if len(schedules) != 2:
                raise ValueError("Expected exact two-schedule feasible set")
            for schedule_id, sequence in schedules.items():
                if len(sequence) != len(set(sequence)):
                    raise ValueError("Duplicate production element")
                evaluations.append(dict(model_family="FAM-A", scenario_id=sid,
                                        schedule_id=schedule_id, production_sequence=" -> ".join(sequence),
                                        lambda_per_min="", mu_per_min="",
                                        state_after_first_manual_kcal_per_min="",
                                        state_after_second_manual_kcal_per_min="",
                                        pre_h2_state_kcal_per_min="", peak_manual_state_kcal_per_min="",
                                        objective_value="", objective_unit="qualitative",
                                        parameter_pair_choice="", model_semantic_choice=""))
            for lam, mu in GRID:
                evaluated = {name: evaluate_b(seq, scenario, lam, mu) for name, seq in schedules.items()}
                first, second = tuple(schedules)
                objective_a, objective_b = evaluated[first]["objective"], evaluated[second]["objective"]
                choice = first if objective_a < objective_b else second if objective_b < objective_a else "TIE"
                pair_choices[sid].append(choice)
                difference = (objective_a - objective_b) if sid == "S1" else (objective_b - objective_a)
                differences[f"{sid}_differences"].append(difference)
                for name, sequence in schedules.items():
                    info = evaluated[name]
                    evaluations.append(dict(model_family="FAM-B", scenario_id=sid,
                                            schedule_id=name, production_sequence=" -> ".join(sequence),
                                            lambda_per_min=lam, mu_per_min=mu,
                                            state_after_first_manual_kcal_per_min=info["state_after_first_manual_kcal_per_min"],
                                            state_after_second_manual_kcal_per_min=info["state_after_second_manual_kcal_per_min"],
                                            pre_h2_state_kcal_per_min=info["pre_h2_state_kcal_per_min"],
                                            peak_manual_state_kcal_per_min=info["peak_manual_state_kcal_per_min"],
                                            objective_value=str(info["objective"]), objective_unit="kcal/min model state",
                                            parameter_pair_choice=choice, model_semantic_choice=""))
    semantic = {"FAM-A": {"S1": "TIE_NO_UNIQUE_TASK_ORDER", "S2": "S2_A"}, "FAM-B": {}}
    for sid in FEASIBLE:
        choices = set(pair_choices[sid])
        semantic["FAM-B"][sid] = next(iter(choices)) if len(choices) == 1 else "PARAMETER_DEPENDENT_NO_UNIQUE_CHOICE"
    for row in evaluations:
        row["model_semantic_choice"] = semantic[row["model_family"]][row["scenario_id"]]
    mapping = []
    for family in ("FAM-A", "FAM-B"):
        for sid, schedules in FEASIBLE.items():
            claim = "ACC" if sid == "S1" else "REC"
            choice = semantic[family][sid]
            robust = "STRUCTURAL" if family == "FAM-A" else str(choice != "PARAMETER_DEPENDENT_NO_UNIQUE_CHOICE").lower()
            for task in TASKS:
                evidence = support[(family, claim, task)]
                status = evidence["status"]
                detail = "EVIDENCE_INSUFFICIENT" if status == "NOT_SUPPORTED" else "POSITIVE_CI"
                if choice == "PARAMETER_DEPENDENT_NO_UNIQUE_CHOICE":
                    after, consequence = "NO_DEFENSIBLE_UNIQUE_CHOICE_FROM_CURRENT_EVIDENCE", "NOT_TESTABLE"
                elif status != "SUPPORTED_FOR_CLAIM" and choice not in ("TIE", "TIE_NO_UNIQUE_TASK_ORDER"):
                    after, consequence = "NO_DEFENSIBLE_UNIQUE_CHOICE_FROM_CURRENT_EVIDENCE", "NARROWED_TO_NO_UNIQUE_CHOICE"
                else:
                    after, consequence = choice, "PRESERVED"
                limit = ("Qualitative structural semantics only; no FAM-A magnitude or rate"
                         if family == "FAM-A" else
                         "Formal source-envelope model state; Keytel-domain bounded; no practical benefit threshold")
                if family == "FAM-B" and sid == "S1" and task == "Composite":
                    limit += "; DEFENSIBLE_FOR_BOUNDED_COMPOSITE_SCENARIO only"
                if detail == "EVIDENCE_INSUFFICIENT":
                    limit += "; insufficiency is not falsification"
                mapping.append(dict(model_family=family, scenario_id=sid, task_context=task,
                                    schedule_a=tuple(schedules)[0], schedule_b=tuple(schedules)[1],
                                    model_semantic_choice=choice, parameter_robust=robust,
                                    required_claim_tags=claim, wp02_support_status=f"{status} — {detail}",
                                    defensible_choice_after_restriction=after,
                                    consequence_class=consequence, interpretation_limit=limit))
    b_s1 = [row for row in mapping if row["model_family"] == "FAM-B" and row["scenario_id"] == "S1"]
    if {row["defensible_choice_after_restriction"] for row in b_s1}.__len__() > 1:
        mapping.append(dict(model_family="FAM-B", scenario_id="S1", task_context="AcrossTasks",
                            schedule_a="S1_A", schedule_b="S1_B", model_semantic_choice=semantic["FAM-B"]["S1"],
                            parameter_robust="true", required_claim_tags="ACC",
                            wp02_support_status="Composite SUPPORTED_FOR_CLAIM; Harnessing NOT_SUPPORTED — EVIDENCE_INSUFFICIENT",
                            defensible_choice_after_restriction="Composite:" + b_s1[0]["defensible_choice_after_restriction"] +
                            ";Harnessing:" + b_s1[1]["defensible_choice_after_restriction"],
                            consequence_class="CONDITIONAL_BY_TASK",
                            interpretation_limit="Task-context evidence mask only; Harnessing is not falsified"))
    if any(row["consequence_class"] not in CONSEQUENCES for row in mapping):
        raise ValueError("Unknown consequence class")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "wp03_schedule_evaluations.csv", EVAL_FIELDS, evaluations)
    write_csv(args.output_dir / "wp03_before_after_claim_map.csv", MAP_FIELDS, mapping)
    report = report_text(scenario, semantic, mapping, differences, digest(args.scenario_inputs))
    (args.output_dir / "WP-03_SCHEDULING_CONSEQUENCE_REPORT.md").write_text(report, encoding="utf-8")
    if digest(args.scenario_inputs) != args.scenario_inputs.with_suffix(".sha256").read_text(encoding="utf-8").split("  ")[0]:
        raise ValueError("Scenario inputs changed during evaluation")
    print(json.dumps({"schedule_evaluation_rows": len(evaluations), "claim_map_rows": len(mapping),
                      "semantic_choices": semantic, "scenario_sha256": digest(args.scenario_inputs)}, indent=2))

if __name__ == "__main__":
    main()
