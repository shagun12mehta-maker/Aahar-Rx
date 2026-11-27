"""
Aahar-Rx Member 2 (Clinical Rules & Data)
Validation and CSV-to-JSON Pipeline
Reads clinical_rules.csv, verifies against schema requirements,
and outputs verified_rules.json ready for Member 4 (Backend API) and Member 3 (UI).
"""

import csv
import json
import os
import sys

REQUIRED_FIELDS = [
    "rule_id",
    "drug_class",
    "active_salts",
    "interfering_nutrients",
    "culprit_indian_foods",
    "severity",
    "interaction_type",
    "safe_before_gap_hrs",
    "safe_after_gap_hrs",
    "bioavailability_drop_pct",
    "t_max_delay_hrs",
    "primary_swap_culprit",
    "primary_swap_substitute",
    "primary_swap_rationale",
    "primary_citation",
    "reviewer_status"
]

def validate_and_convert(csv_path: str, json_out_path: str):
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found at: {csv_path}")
        return False

    records = []
    errors = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = [col for col in REQUIRED_FIELDS if col not in reader.fieldnames]
        if missing_cols:
            print(f"[FATAL] CSV is missing essential columns: {missing_cols}")
            return False

        for row_idx, row in enumerate(reader, start=2):
            rule_id = row.get("rule_id", "").strip()
            if not rule_id:
                errors.append(f"Row {row_idx}: Missing rule_id")
                continue

            # Parse arrays separated by ';'
            salts = [s.strip() for s in row.get("active_salts", "").split(";") if s.strip()]
            nutrients = [n.strip() for n in row.get("interfering_nutrients", "").split(";") if n.strip()]
            foods = [fd.strip() for fd in row.get("culprit_indian_foods", "").split(";") if fd.strip()]

            if not salts:
                errors.append(f"Row {row_idx} ({rule_id}): active_salts cannot be empty")
            if not foods:
                errors.append(f"Row {row_idx} ({rule_id}): culprit_indian_foods cannot be empty")

            # Numeric validations
            try:
                before_gap = float(row.get("safe_before_gap_hrs", 0))
                after_gap = float(row.get("safe_after_gap_hrs", 0))
                bio_drop = float(row.get("bioavailability_drop_pct", 0))
                t_max = float(row.get("t_max_delay_hrs", 0))
            except ValueError as ve:
                errors.append(f"Row {row_idx} ({rule_id}): Numeric parse failure - {ve}")
                continue

            # Check citations
            citations_raw = [c.strip() for c in row.get("primary_citation", "").split(";") if c.strip()]
            citations_list = []
            for c in citations_raw:
                parts = c.split(" ", 1)
                source_name = parts[0] if len(parts) > 0 else "Unknown"
                ref_id = parts[1] if len(parts) > 1 else c
                citations_list.append({"source": source_name, "reference_id": ref_id})

            severity = row.get("severity", "MODERATE").strip().upper()
            high_risk_raw = row.get("high_risk_clash", "").strip().upper()
            high_risk_clash = high_risk_raw in {"TRUE", "1", "YES"} if high_risk_raw else (severity == "HIGH")
            high_risk_reason = row.get("high_risk_reason", "").strip()

            record = {
                "rule_id": rule_id,
                "drug_class": row.get("drug_class", "").strip(),
                "active_salts": salts,
                "interfering_nutrients": nutrients,
                "culprit_indian_foods": foods,
                "severity": severity,
                "high_risk_clash": high_risk_clash,
                "high_risk_reason": high_risk_reason,
                "interaction_type": row.get("interaction_type", "").strip(),
                "safe_time_gap_hours": {
                    "before_food_hours": before_gap,
                    "after_food_hours": after_gap
                },
                "absorption_impact": {
                    "bioavailability_drop_pct": bio_drop,
                    "t_max_delay_hours": t_max
                },
                "ghar_ki_rasoi_swaps": [
                    {
                        "culprit": row.get("primary_swap_culprit", "").strip(),
                        "substitute": row.get("primary_swap_substitute", "").strip(),
                        "dietary_rationale": row.get("primary_swap_rationale", "").strip()
                    }
                ],
                "citations": citations_list,
                "clinical_sign_off": {
                    "reviewed": True if row.get("reviewer_status", "").strip().upper() == "APPROVED" else False,
                    "reviewer_role": "Clinical Dietitian / MD Reviewer",
                    "status": row.get("reviewer_status", "PENDING").strip().upper()
                }
            }
            records.append(record)

    if errors:
        print("[VALIDATION ERRORS FOUND]:")
        for err in errors:
            print(f"  - {err}")
        return False

    with open(json_out_path, mode="w", encoding="utf-8") as out:
        json.dump(records, out, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Validated {len(records)} clinical rules successfully!")
    print(f"Generated clean export at: {json_out_path}")
    return True

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, ".."))
    
    # Check data/ directory first, fallback to current dir
    candidate_csv = os.path.join(repo_root, "data", "clinical_rules.csv")
    if os.path.exists(candidate_csv):
        default_csv = candidate_csv
        default_json = os.path.join(repo_root, "data", "verified_rules.json")
    else:
        default_csv = os.path.join(current_dir, "clinical_rules.csv")
        default_json = os.path.join(current_dir, "verified_rules.json")

    success = validate_and_convert(default_csv, default_json)
    if not success:
        sys.exit(1)
