"""Freeze WP-03 representative values from Stage-A model inputs only."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
sys.path.insert(0, str(ROOT / "scripts"))
from wp02_predict_blind import EXPECTED_INPUT, keytel

AUTHORITY_FILES = (
    "artifacts/WP-03_SCHEDULING_CONSEQUENCE_CONTRACT_v1.md",
    "artifacts/WP-02_CONTROLLER_ADJUDICATION_2026-09-26.md",
    "artifacts/EVIDENCE_MAP_FATIGUE_VALID_v1.md",
    "artifacts/WP-02_COMPARATIVE_BEHAVIOR_VALIDATION_REPORT.md",
    "artifacts/wp02_behavior_evidence_table.csv",
    "artifacts/PARAMETER_RULE_AUTHORITY_FATIGUE_VALID_v1.md",
    "artifacts/analysis_contract_FATIGUE_VALID_v2.yaml",
    "artifacts/validation_endpoint_contract_FATIGUE_VALID_v2.md",
    "artifacts/SCIENTIFIC_CONTRIBUTION_CONTRACT_FATIGUE_VALID_v1.md",
)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def percentile_type7(values, fraction):
    ordered = sorted(values)
    h = (len(ordered) - 1) * fraction
    lower, upper = math.floor(h), math.ceil(h)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (h - lower)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    parser.add_argument("--timestamp", default=None, help="fixed UTC timestamp for clean reproduction")
    args = parser.parse_args()
    output = args.output_dir / "wp03_scenario_inputs.json"
    seal = args.output_dir / "wp03_scenario_inputs.sha256"
    if output.exists() or seal.exists():
        raise FileExistsError("WP-03 scenario inputs already frozen; use a fresh output directory")
    source = ART / "wp02_model_inputs_blind.csv"
    stage_a = json.loads((ART / "wp02_stage_a_manifest.json").read_text(encoding="utf-8"))
    if digest(source) != stage_a["input_file_hashes_sha256"]["artifacts/wp02_model_inputs_blind.csv"]:
        raise ValueError("Stage-A model input hash mismatch")
    freeze_lines = (ART / "wp02_stage_a_freeze.sha256").read_text(encoding="utf-8").splitlines()
    if f"{digest(source)}  wp02_model_inputs_blind.csv" not in freeze_lines:
        raise ValueError("Stage-A input is not in the frozen SHA-256 list")
    with source.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != EXPECTED_INPUT:
            raise ValueError("Unexpected input schema; Borg fields are forbidden")
        rows = list(reader)
    work = [row for row in rows if row["primary_b"] == "1" and
            row["segment_id"] in {f"Rep{i}" for i in range(1, 6)} and
            float(row["duration_seconds"]) >= 60 and
            row["hr_qualified_mean_bpm"] and int(row["hr_qualified_sample_count"]) > 0]
    if not work:
        raise ValueError("No eligible frozen work-segment inputs")
    eer = [keytel(row) for row in work]
    durations = [float(row["duration_seconds"]) / 60 for row in work]
    if not all(math.isfinite(value) for value in eer + durations):
        raise ValueError("Nonfinite representative source inputs")
    eligible_people = sorted({row["participant_id"] for row in work})
    scenario = {
        "schema_version": "wp03-scenario-inputs-1.0",
        "created_utc": args.timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_input_file": "artifacts/wp02_model_inputs_blind.csv",
        "source_input_sha256": digest(source),
        "stage_a_manifest_sha256": digest(ART / "wp02_stage_a_manifest.json"),
        "stage_a_freeze_sha256": digest(ART / "wp02_stage_a_freeze.sha256"),
        "authority_file_hashes_sha256": {name: digest(ROOT / name) for name in AUTHORITY_FILES},
        "code_file_hashes_sha256": {
            "scripts/wp03_build_scenarios.py": digest(Path(__file__)),
            "scripts/wp02_predict_blind.py": digest(ROOT / "scripts/wp02_predict_blind.py"),
        },
        "eligible_work_segment_count": len(work),
        "eligible_participant_count": len(eligible_people),
        "eligibility_rule": "primary_b=1; Rep1-Rep5; duration>=60s; positive SQI>0.5-qualified HR count",
        "keytel_rule": "frozen wp02_predict_blind.keytel: HR mean bpm, age years, weight lb to kg, Gender 0/1; work only",
        "percentile_rule": "type-7 linear interpolation at (n-1)*p; pooled across eligible work segments",
        "E_L_kcal_per_min": percentile_type7(eer, 0.25),
        "E_H_kcal_per_min": percentile_type7(eer, 0.75),
        "D_minutes": statistics.median(durations),
        "R_minutes": 5.0,
        "E_R_kcal_per_min": 1.86,
        "outcome_blind_confirmation": "Only the exact Stage-A input-table allowlist supplied representative values; no Borg, agreement score or schedule result was accessed.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
    seal.write_text(f"{digest(output)}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"eligible_work_segments": len(work), "E_L": scenario["E_L_kcal_per_min"],
                      "E_H": scenario["E_H_kcal_per_min"], "D": scenario["D_minutes"],
                      "R": scenario["R_minutes"], "scenario_sha256": digest(output)}, indent=2))

if __name__ == "__main__":
    main()
