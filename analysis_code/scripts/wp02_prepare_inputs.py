"""Project processed CSVs into an input-only WP-02 table.

This script selects only Time, HR, ECGSQI, Age, Weight and Gender cells by
column index. It never indexes, stores or evaluates any Borg column value.
The prediction process reads only the resulting allowlisted table.
"""
from pathlib import Path
import argparse
import csv
import json
import math

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
INVENTORY = ART / "participant_task_segment_inventory.csv"
APPLICABILITY = ART / "keytel_applicability.csv"
SOURCE_COLUMNS = ("Time", "HR", "ECGSQI", "Age", "Weight", "Gender")
FORBIDDEN_TOKENS = ("fatigue", "borg", "mental", "performance", "hrv", "temperature", "imu")
INPUT_COLUMNS = (
    "participant_id", "task_id", "task_name", "segment_id", "segment_order",
    "segment_type", "duration_seconds", "source_file", "primary_a", "primary_b",
    "hr_qualified_mean_bpm", "hr_qualified_sample_count", "age_years", "weight_lb",
    "gender_code",
)

def finite(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) else None

def project_source(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        indices = tuple(header.index(name) for name in SOURCE_COLUMNS)
        assert all(not any(token in name.lower() for token in FORBIDDEN_TOKENS)
                   for name in SOURCE_COLUMNS)
        qualified_hr = []
        demographics = {name: set() for name in ("Age", "Weight", "Gender")}
        for raw_row in reader:
            # The CSV parser frames rows, but only these six allowed indices are accessed.
            selected = dict(zip(SOURCE_COLUMNS, (raw_row[index] for index in indices)))
            for name in demographics:
                value = finite(selected[name])
                if value is not None:
                    demographics[name].add(value)
            hr = finite(selected["HR"])
            sqi = finite(selected["ECGSQI"])
            if hr is not None and hr > 0 and sqi is not None and sqi > 0.5:
                qualified_hr.append(hr)
    if any(len(values) > 1 for values in demographics.values()):
        raise ValueError(f"Demographic varies within segment: {path}")
    return (
        math.fsum(qualified_hr) / len(qualified_hr) if qualified_hr else None,
        len(qualified_hr),
        {name: next(iter(values)) if values else None for name, values in demographics.items()},
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    output = args.output_dir / "wp02_model_inputs_blind.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    primary_b_ids = {
        row["participant_id"] for row in csv.DictReader(APPLICABILITY.open(encoding="utf-8"))
        if row["primary_applicable"] == "1"
    }
    # Private, locally supplied exclusion file; not distributed in this package.
    private = json.loads((ROOT / "private_inputs" / "primary_a_exclusions.json").read_text(encoding="utf-8"))
    primary_a_exclusions = set(private["excluded_identifiers"])
    rows = []
    for item in csv.DictReader(INVENTORY.open(encoding="utf-8")):
        participant = item["participant_id"]
        mean_hr, hr_count, demo = project_source(ROOT / item["source_file"])
        rows.append({
            "participant_id": participant, "task_id": item["task_id"],
            "task_name": item["task_name"], "segment_id": item["segment_id"],
            "segment_order": item["segment_order"], "segment_type": item["segment_type"],
            "duration_seconds": item["duration"], "source_file": item["source_file"],
            "primary_a": int(participant not in primary_a_exclusions),
            "primary_b": int(participant in primary_b_ids),
            "hr_qualified_mean_bpm": f"{mean_hr:.12g}" if mean_hr is not None else "",
            "hr_qualified_sample_count": hr_count,
            "age_years": demo["Age"] if demo["Age"] is not None else "",
            "weight_lb": demo["Weight"] if demo["Weight"] is not None else "",
            "gender_code": int(demo["Gender"]) if demo["Gender"] is not None else "",
        })
    assert len(rows) == 521
    assert not any(any(token in field.lower() for token in FORBIDDEN_TOKENS)
                   for field in INPUT_COLUMNS)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=INPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Projected {len(rows)} input-only segment rows to {output}")

if __name__ == "__main__":
    main()
