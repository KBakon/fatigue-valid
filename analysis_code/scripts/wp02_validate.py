"""Stage B: ordinal Borg validation of immutable Stage-A predictions."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
SEED = 20260926
N_BOOT = 10000
ENDPOINTS = ("ACC_A", "PF_REL_A", "REC_A", "ACC_B", "REC_B")
TASKS = ("Composite", "Harnessing")
TRANS_FIELDS = ("prediction_id", "endpoint_id", "model_family", "claim_tag", "participant_id",
                "task", "from_segment", "to_segment", "predicted_direction", "observed_direction", "agreement")
PART_FIELDS = ("endpoint_id", "model_family", "claim_tag", "participant_id", "task", "metric",
               "eligible_transitions", "observed_up", "observed_tie", "observed_down", "participant_score")
SUMMARY_FIELDS = ("endpoint_id", "model_family", "claim_tag", "task", "metric", "eligible_participants",
                  "eligible_transitions", "observed_up", "observed_tie", "observed_down",
                  "participant_score_distribution_json", "mean_participant_score", "median_participant_score",
                  "ci_lower", "ci_upper", "status", "status_detail")
EVIDENCE_FIELDS = ("model_family", "claim_tag", "task", "primary_n", "prediction_robust_n",
                   "endpoint_metric", "estimate", "ci_lower", "ci_upper", "status", "boundary",
                   "interpretation_limit", "artifact_source")
PAIRED_FIELDS = ("endpoint_id", "claim_tag", "metric", "paired_participants", "participant_ids_json",
                 "mean_composite_minus_harnessing", "ci_lower", "ci_upper", "interpretation_limit")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def write_csv(path, fields, data):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)

def verify_freeze(stage_dir):
    """This runs before any source/Borg file is opened."""
    manifest_path = stage_dir / "wp02_stage_a_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["stage"] != "A" or not manifest["outcome_blind"]:
        raise ValueError("Stage-A blind assertion missing")
    freeze = stage_dir / "wp02_stage_a_freeze.sha256"
    frozen = {}
    for line in freeze.read_text(encoding="utf-8").splitlines():
        sha, name = line.split("  ", 1)
        if name in frozen or name not in {"wp02_model_inputs_blind.csv", "wp02_model_predictions_blind.csv",
                                              "wp02_prediction_robustness.json", "wp02_stage_a_manifest.json"}:
            raise ValueError("Unexpected Stage-A freeze entry")
        frozen[name] = sha
    if len(frozen) != 4:
        raise ValueError("Incomplete Stage-A freeze")
    for name, sha in frozen.items():
        if digest(stage_dir / name) != sha:
            raise ValueError(f"Stage-A hash mismatch: {name}")
    if digest(stage_dir / "wp02_model_predictions_blind.csv") != manifest["prediction_artifact_sha256"]:
        raise ValueError("Prediction manifest hash mismatch")
    if digest(stage_dir / "wp02_prediction_robustness.json") != manifest["robustness_artifact_sha256"]:
        raise ValueError("Robustness manifest hash mismatch")
    for name, sha in manifest["authority_file_hashes_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Authority changed: {name}")
    for name, sha in manifest["code_file_hashes_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Stage-A code changed: {name}")
    for name, sha in manifest["input_file_hashes_sha256"].items():
        path = stage_dir / "wp02_model_inputs_blind.csv" if name.endswith("wp02_model_inputs_blind.csv") else ROOT / name
        if digest(path) != sha:
            raise ValueError(f"Input changed: {name}")
    return manifest, frozen

def physical_borg(path):
    """Read only the two original physical Borg cells by column index."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        indices = (header.index("Physical Fatigue - Initial"), header.index("Physical Fatigue - Final"))
        values = (set(), set())
        for raw in reader:
            for idx, found in zip(indices, values):
                value = raw[idx].strip()
                if value:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError(f"Nonfinite physical Borg: {path}")
                    found.add(number)
    if any(len(found) > 1 for found in values):
        raise ValueError(f"Physical Borg varies within segment: {path}")
    return tuple(next(iter(found)) if found else None for found in values)

def sign(x):
    return (x > 0) - (x < 0)

def tau_b_order(values):
    concordant = discordant = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            delta = sign(values[j] - values[i])
            concordant += delta > 0
            discordant += delta < 0
    untied = concordant + discordant
    return (concordant - discordant) / math.sqrt(untied * 10) if untied else None

def percentile(sorted_values, q):
    place = (len(sorted_values) - 1) * q
    lo = math.floor(place)
    hi = math.ceil(place)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (place - lo)

def boot_ci(values):
    if not values:
        return None, None
    rng = random.Random(SEED)
    n = len(values)
    means = sorted(math.fsum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(N_BOOT))
    return percentile(means, 0.025), percentile(means, 0.975)

def status(lo, hi):
    if lo is None:
        return "NOT_TESTABLE", "NO_ELIGIBLE_PARTICIPANTS"
    if lo > 0:
        return "SUPPORTED_FOR_CLAIM", "POSITIVE_CI"
    if hi < 0:
        return "NOT_SUPPORTED", "DIRECTIONALLY_CONTRADICTED"
    return "NOT_SUPPORTED", "EVIDENCE_INSUFFICIENT"

def fmt(value):
    return "" if value is None else f"{value:.12g}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-a-dir", type=Path, default=ART)
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    manifest, frozen = verify_freeze(args.stage_a_dir)
    # No Borg access is possible before this point. Only frozen predictions are used.
    predictions = rows(args.stage_a_dir / "wp02_model_predictions_blind.csv")
    inputs = rows(args.stage_a_dir / "wp02_model_inputs_blind.csv")
    if len(predictions) != manifest["prediction_row_count"] or manifest["parameter_pair_count"] != 20:
        raise ValueError("Frozen prediction count or parameter grid changed")
    for p in predictions:
        if p["model_family"] == "FAM-B":
            pairs = json.loads(p["pair_directions_json"])
            if len(pairs) != 20 or int(p["n_parameter_pairs"]) != 20:
                raise ValueError("Incomplete B parameter envelope")
            if p["prediction_status"] == "PARAMETER_ROBUST_PREDICTION" and len({x["direction"] for x in pairs}) != 1:
                raise ValueError("Invalid robustness label")
    source = {(r["participant_id"], r["task_name"], r["segment_id"]): ROOT / r["source_file"] for r in inputs}
    needed = set()
    for p in predictions:
        if p["model_family"] == "FAM-B" and p["prediction_status"] != "PARAMETER_ROBUST_PREDICTION":
            continue
        key = (p["participant_id"], p["task"])
        if p["endpoint_id"] == "PF_REL_A":
            needed.update((key[0], key[1], f"Rep{i}") for i in range(1, 6))
        else:
            needed.add((key[0], key[1], p["to_segment"]))
            if p["endpoint_id"].startswith("ACC"):
                needed.add((key[0], key[1], p["from_segment"]))
    labels = {key: physical_borg(source[key]) for key in sorted(needed)}
    transitions = []
    tau_rows = []
    for p in predictions:
        if p["model_family"] == "FAM-B" and p["prediction_status"] != "PARAMETER_ROBUST_PREDICTION":
            continue
        pid, task, endpoint = p["participant_id"], p["task"], p["endpoint_id"]
        if endpoint == "PF_REL_A":
            work = [labels[(pid, task, f"Rep{i}")][1] for i in range(1, 6)]
            if all(value is not None for value in work):
                tau = tau_b_order(work)
                if tau is not None:
                    tau_rows.append(dict(endpoint_id=endpoint, model_family="FAM-A", claim_tag="PF_REL",
                                         participant_id=pid, task=task, metric="kendall_tau_b",
                                         eligible_transitions=0, observed_up="", observed_tie="", observed_down="",
                                         participant_score=fmt(tau)))
            continue
        if endpoint.startswith("ACC"):
            first = labels[(pid, task, p["from_segment"])][1]
            last = labels[(pid, task, p["to_segment"])][1]
        else:
            first, last = labels[(pid, task, "Final_Rest")]
        if first is None or last is None:
            continue
        observed = sign(last - first)
        predicted = int(p["predicted_direction"])
        agreement = 0 if observed == 0 or predicted == 0 else 1 if observed == predicted else -1
        transitions.append({key: p[key] for key in ("prediction_id", "endpoint_id", "model_family", "claim_tag",
                                                       "participant_id", "task", "from_segment", "to_segment")}
                           | {"predicted_direction": predicted, "observed_direction": observed, "agreement": agreement})
    grouped = defaultdict(list)
    for row in transitions:
        grouped[(row["endpoint_id"], row["task"], row["participant_id"])].append(row)
    participants = []
    for (endpoint, task, pid), group in sorted(grouped.items()):
        participants.append(dict(endpoint_id=endpoint, model_family=group[0]["model_family"],
                                 claim_tag=group[0]["claim_tag"], participant_id=pid, task=task,
                                 metric="direction_agreement", eligible_transitions=len(group),
                                 observed_up=sum(row["observed_direction"] == 1 for row in group),
                                 observed_tie=sum(row["observed_direction"] == 0 for row in group),
                                 observed_down=sum(row["observed_direction"] == -1 for row in group),
                                 participant_score=fmt(statistics.mean(row["agreement"] for row in group))))
    participants += tau_rows
    participants.sort(key=lambda r: (r["endpoint_id"], r["task"], r["participant_id"]))
    summaries = []
    evidence = []
    by_endpoint_task = defaultdict(list)
    for row in participants:
        by_endpoint_task[(row["endpoint_id"], row["task"])].append(row)
    for endpoint in ENDPOINTS:
        for task in TASKS:
            group = by_endpoint_task[(endpoint, task)]
            selected = [float(row["participant_score"]) for row in group]
            lo, hi = boot_ci(selected)
            family = "FAM-A" if endpoint.endswith("_A") else "FAM-B"
            claim = "PF_REL" if endpoint == "PF_REL_A" else endpoint.split("_")[0]
            metric = "kendall_tau_b" if endpoint == "PF_REL_A" else "direction_agreement"
            n_transition = sum(int(row["eligible_transitions"]) for row in group)
            count_up = sum(int(row["observed_up"] or 0) for row in group)
            count_tie = sum(int(row["observed_tie"] or 0) for row in group)
            count_down = sum(int(row["observed_down"] or 0) for row in group)
            state, detail = status(lo, hi)
            summary = dict(endpoint_id=endpoint, model_family=family, claim_tag=claim, task=task,
                           metric=metric, eligible_participants=len(group), eligible_transitions=n_transition,
                           observed_up=count_up, observed_tie=count_tie, observed_down=count_down,
                           participant_score_distribution_json=json.dumps(selected, separators=(",", ":")),
                           mean_participant_score=fmt(statistics.mean(selected)) if selected else "",
                           median_participant_score=fmt(statistics.median(selected)) if selected else "",
                           ci_lower=fmt(lo), ci_upper=fmt(hi), status=state, status_detail=detail)
            summaries.append(summary)
            robust_n = sum(p["endpoint_id"] == endpoint and p["task"] == task and
                           p["prediction_status"] in ("PARAMETER_ROBUST_PREDICTION", "STRUCTURAL_ROBUST_PREDICTION")
                           for p in predictions)
            boundary = "Ordinal physical Borg; participant-level uncertainty; source-reference parameter envelope"
            if family == "FAM-B":
                boundary += "; Keytel primary domain and SQI-qualified work HR"
            evidence.append(dict(model_family=family, claim_tag=claim, task=task, primary_n=len(group),
                                 prediction_robust_n=robust_n, endpoint_metric=metric,
                                 estimate=summary["mean_participant_score"], ci_lower=summary["ci_lower"],
                                 ci_upper=summary["ci_upper"], status=state, boundary=boundary,
                                 interpretation_limit=detail + "; ordinal direction/association only; no magnitude equality or equivalence",
                                 artifact_source="artifacts/wp02_endpoint_results.csv"))
    paired = []
    for endpoint in ENDPOINTS:
        comp = {row["participant_id"]: float(row["participant_score"]) for row in by_endpoint_task[(endpoint, "Composite")]}
        harness = {row["participant_id"]: float(row["participant_score"]) for row in by_endpoint_task[(endpoint, "Harnessing")]}
        ids = sorted(comp.keys() & harness.keys())
        differences = [comp[pid] - harness[pid] for pid in ids]
        lo, hi = boot_ci(differences)
        paired.append(dict(endpoint_id=endpoint, claim_tag="TASK",
                           metric="paired_kendall_tau_b_difference" if endpoint == "PF_REL_A" else "paired_agreement_difference",
                           paired_participants=len(ids), participant_ids_json=json.dumps(ids, separators=(",", ":")),
                           mean_composite_minus_harnessing=fmt(statistics.mean(differences)) if differences else "",
                           ci_lower=fmt(lo), ci_upper=fmt(hi),
                           interpretation_limit="Descriptive paired task contrast; no equivalence margin or task superiority claim"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "wp02_transition_level_results.csv", TRANS_FIELDS, transitions)
    write_csv(args.output_dir / "wp02_participant_level_results.csv", PART_FIELDS, participants)
    write_csv(args.output_dir / "wp02_endpoint_results.csv", SUMMARY_FIELDS, summaries)
    write_csv(args.output_dir / "wp02_behavior_evidence_table.csv", EVIDENCE_FIELDS, evidence)
    write_csv(args.output_dir / "wp02_task_pair_results.csv", PAIRED_FIELDS, paired)
    for name, sha in frozen.items():
        if digest(args.stage_a_dir / name) != sha:
            raise ValueError(f"Stage A was modified during Stage B: {name}")
    stage_b_manifest = {
        "stage": "B", "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "consumed_stage_a_manifest_sha256": frozen["wp02_stage_a_manifest.json"],
        "stage_a_unchanged_after_borg_access": True,
        "validation_channel": "original physical Borg; ordinal only",
        "bootstrap_unit": "participant", "bootstrap_resamples": N_BOOT, "bootstrap_seed": SEED,
        "output_hashes_sha256": {name: digest(args.output_dir / name) for name in
                                 ("wp02_transition_level_results.csv", "wp02_participant_level_results.csv",
                                  "wp02_endpoint_results.csv", "wp02_behavior_evidence_table.csv",
                                  "wp02_task_pair_results.csv")},
    }
    (args.output_dir / "wp02_stage_b_manifest.json").write_text(json.dumps(stage_b_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"transition_rows": len(transitions), "participant_rows": len(participants),
                      "endpoint_rows": len(summaries), "paired_rows": len(paired)}, indent=2))

if __name__ == "__main__":
    main()
