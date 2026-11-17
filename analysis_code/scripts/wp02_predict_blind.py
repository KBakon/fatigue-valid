"""Stage A: model predictions from an input-only table, with no Borg access.

The only participant-level file this process opens is the allowlisted model
input table from wp02_prepare_inputs.py. Borg columns cause an immediate error.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import itertools
import json
import math

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
FORBIDDEN = ("fatigue", "borg", "mental", "performance", "hrv", "temperature", "imu")
EXPECTED_INPUT = {
    "participant_id", "task_id", "task_name", "segment_id", "segment_order", "segment_type",
    "duration_seconds", "source_file", "primary_a", "primary_b", "hr_qualified_mean_bpm",
    "hr_qualified_sample_count", "age_years", "weight_lb", "gender_code",
}
GRID = tuple(itertools.product((2, 4, 6, 8, 10), (0.5, 1, 1.5, 2)))
E_R = 1.86
PRED_FIELDS = (
    "prediction_id", "model_family", "endpoint_id", "claim_tag", "participant_id",
    "task", "from_segment", "to_segment", "predicted_direction", "prediction_status",
    "n_parameter_pairs", "pair_directions_json", "input_boundary",
)
AUTHORITY_FILES = (
    "artifacts/PARAMETER_RULE_AUTHORITY_FATIGUE_VALID_v1.md",
    "artifacts/analysis_contract_FATIGUE_VALID_v2.yaml",
    "artifacts/validation_endpoint_contract_FATIGUE_VALID_v2.md",
    "artifacts/WP-01B_CONTROLLER_ADJUDICATION_2026-09-26.md",
    "artifacts/SCIENTIFIC_CONTRIBUTION_CONTRACT_FATIGUE_VALID_v1.md",
    "artifacts/WP-01A_CORPUS_FREEZE_REPORT_2026-09-26.md",
)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sign(x):
    return (x > 0) - (x < 0)

def keytel(row):
    hr = float(row["hr_qualified_mean_bpm"])
    age = float(row["age_years"])
    kg = float(row["weight_lb"]) / 2.20462262185
    gender = int(row["gender_code"])
    if gender == 0:
        kj_min = -55.0969 + 0.6309 * hr + 0.1988 * kg + 0.2017 * age
    elif gender == 1:
        kj_min = -20.4022 + 0.4472 * hr - 0.1263 * kg + 0.0740 * age
    else:
        raise ValueError(f"Unsupported gender code: {gender}")
    return kj_min / 4.184

def qualified(row, *, need_hr=False):
    if float(row["duration_seconds"]) < 60:
        return False
    if need_hr and (not row["hr_qualified_mean_bpm"] or int(row["hr_qualified_sample_count"]) == 0):
        return False
    return True

def make_prediction(family, endpoint, participant, task, start, end, directions, boundary):
    if family == "FAM-A":
        status = "STRUCTURAL_ROBUST_PREDICTION"
        direction = directions[0]
        pair_json = ""
        n_pairs = 0
    else:
        n_pairs = len(directions)
        assert n_pairs == 20
        status = "PARAMETER_ROBUST_PREDICTION" if len(set(directions)) == 1 else "PARAMETER_DEPENDENT_NOT_TESTABLE"
        direction = directions[0] if status == "PARAMETER_ROBUST_PREDICTION" else ""
        pair_json = json.dumps([{"lambda": lam, "mu": mu, "direction": value}
                                for (lam, mu), value in zip(GRID, directions)], separators=(",", ":"))
    return {
        "prediction_id": f"{family}|{endpoint}|{task}|{participant}|{start}|{end}",
        "model_family": family, "endpoint_id": endpoint,
        "claim_tag": "PF_REL" if endpoint == "PF_REL_A" else "ACC" if endpoint.startswith("ACC") else "REC",
        "participant_id": participant, "task": task, "from_segment": start, "to_segment": end,
        "predicted_direction": direction, "prediction_status": status,
        "n_parameter_pairs": n_pairs, "pair_directions_json": pair_json, "input_boundary": boundary,
    }

def predict(inputs):
    by_pair = defaultdict(dict)
    for row in inputs:
        key = (row["participant_id"], row["task_name"])
        if row["segment_id"] in by_pair[key]:
            raise ValueError(f"Duplicate segment: {key} {row['segment_id']}")
        by_pair[key][row["segment_id"]] = row
    outputs = []
    skipped = Counter()
    for (participant, task), segments in sorted(by_pair.items()):
        if all(segments[s]["primary_a"] == "1" for s in segments):
            work = [segments.get(f"Rep{i}") for i in range(1, 6)]
            if all(row is not None and qualified(row) for row in work):
                for j in range(1, 5):
                    outputs.append(make_prediction("FAM-A", "ACC_A", participant, task,
                                                   f"Rep{j}", f"Rep{j+1}", [1], "complete_five_work_segments"))
                outputs.append(make_prediction("FAM-A", "PF_REL_A", participant, task,
                                               "Rep1", "Rep5", [1], "complete_five_work_segments"))
            else:
                skipped[("FAM-A", "ACC_A", task, "INCOMPLETE_OR_SHORT_WORK")] += 1
            rep5, final_rest = segments.get("Rep5"), segments.get("Final_Rest")
            if rep5 is not None and final_rest is not None and qualified(rep5) and qualified(final_rest):
                outputs.append(make_prediction("FAM-A", "REC_A", participant, task,
                                               "Rep5", "Final_Rest", [-1], "actual_final_rest_transition"))
            else:
                skipped[("FAM-A", "REC_A", task, "MISSING_OR_SHORT_REST_TRANSITION")] += 1
        if not all(row["primary_b"] == "1" for row in segments.values()):
            continue
        # One trajectory per source-reference pair; never infer a missing prior work state.
        states = {pair: E_R for pair in GRID}
        ends = {}
        broken = False
        for j in range(1, 6):
            name = f"Rep{j}"
            row = segments.get(name)
            if broken or row is None or not qualified(row, need_hr=True):
                broken = True
                skipped[("FAM-B", "WORK", task, f"STATE_UNAVAILABLE_AT_{name}")] += 1
                continue
            ew = keytel(row)
            minutes = float(row["duration_seconds"]) / 60
            next_states = {}
            for lam, mu in GRID:
                prior = states[(lam, mu)]
                rate = lam if ew >= prior else mu
                next_states[(lam, mu)] = ew + (prior - ew) * math.exp(-rate * minutes)
            states = next_states
            ends[name] = states.copy()
            if j > 1 and f"Rep{j-1}" in ends:
                directions = [sign(ends[name][pair] - ends[f"Rep{j-1}"][pair]) for pair in GRID]
                outputs.append(make_prediction("FAM-B", "ACC_B", participant, task,
                                               f"Rep{j-1}", name, directions, "observed_contiguous_prefix"))
        rest = segments.get("Final_Rest")
        if "Rep5" in ends and rest is not None and qualified(rest):
            minutes = float(rest["duration_seconds"]) / 60
            directions = [sign(max(E_R, ends["Rep5"][pair] * math.exp(-pair[1] * minutes))
                               - ends["Rep5"][pair]) for pair in GRID]
            outputs.append(make_prediction("FAM-B", "REC_B", participant, task,
                                           "Rep5", "Final_Rest", directions, "source_exponential_with_rest_floor"))
        else:
            skipped[("FAM-B", "REC_B", task, "STATE_OR_REST_UNAVAILABLE")] += 1
    return sorted(outputs, key=lambda row: row["prediction_id"]), skipped

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-table", type=Path, default=ART / "wp02_model_inputs_blind.csv")
    parser.add_argument("--output-dir", type=Path, default=ART)
    parser.add_argument("--timestamp", default=None, help="UTC ISO timestamp for deterministic reproduction")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.input_table.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        names = set(reader.fieldnames or ())
        if names != EXPECTED_INPUT or any(any(token in name.lower() for token in FORBIDDEN) for name in names):
            raise ValueError("Model input table must have exact outcome-free allowlist columns")
        inputs = list(reader)
    assert len(inputs) == 521
    predictions, skipped = predict(inputs)
    pred_path = args.output_dir / "wp02_model_predictions_blind.csv"
    with pred_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PRED_FIELDS)
        writer.writeheader()
        writer.writerows(predictions)
    by_group = Counter((r["model_family"], r["endpoint_id"], r["task"], r["prediction_status"])
                       for r in predictions)
    robustness = {
        "source_reference_pairs": [{"lambda": lam, "mu": mu} for lam, mu in GRID],
        "pair_count": len(GRID),
        "prediction_counts": [dict(model_family=f, endpoint_id=e, task=t, status=s, count=n)
                              for (f, e, t, s), n in sorted(by_group.items())],
        "input_unavailable_counts": [dict(model_family=f, endpoint_id=e, task=t, reason=s, count=n)
                                     for (f, e, t, s), n in sorted(skipped.items())],
    }
    robust_path = args.output_dir / "wp02_prediction_robustness.json"
    robust_path.write_text(json.dumps(robustness, indent=2) + "\n", encoding="utf-8")
    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "stage": "A", "created_utc": timestamp, "outcome_blind": True,
        "borg_columns_inaccessible_to_prediction_process": True,
        "prediction_input_schema": sorted(EXPECTED_INPUT),
        "input_file_hashes_sha256": {
            "artifacts/wp02_model_inputs_blind.csv": digest(args.input_table),
            "artifacts/participant_task_segment_inventory.csv": digest(ART / "participant_task_segment_inventory.csv"),
            "artifacts/keytel_applicability.csv": digest(ART / "keytel_applicability.csv"),
        },
        "authority_file_hashes_sha256": {name: digest(ROOT / name) for name in AUTHORITY_FILES},
        "code_version": "wp02-stage-a-1.0",
        "code_file_hashes_sha256": {
            "scripts/wp02_prepare_inputs.py": digest(ROOT / "scripts/wp02_prepare_inputs.py"),
            "scripts/wp02_predict_blind.py": digest(ROOT / "scripts/wp02_predict_blind.py"),
        },
        "prediction_artifact_sha256": digest(pred_path),
        "robustness_artifact_sha256": digest(robust_path),
        "parameter_pair_count": len(GRID),
        "prediction_row_count": len(predictions),
        "confirmation": "Prediction process opened only the allowlisted model-input table; Borg values were inaccessible and not read.",
    }
    manifest_path = args.output_dir / "wp02_stage_a_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    freeze_path = args.output_dir / "wp02_stage_a_freeze.sha256"
    freeze_path.write_text("".join(f"{digest(path)}  {path.name}\n" for path in
                                   (args.input_table, pred_path, robust_path, manifest_path)), encoding="utf-8")
    print(json.dumps({"prediction_rows": len(predictions), "pair_count": len(GRID),
                      "prediction_sha256": manifest["prediction_artifact_sha256"],
                      "robustness_sha256": manifest["robustness_artifact_sha256"],
                      "manifest_sha256": digest(manifest_path)}, indent=2))

if __name__ == "__main__":
    main()
