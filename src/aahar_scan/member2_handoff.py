"""Schema validation and Member 2 verified_rules.json / CSV compatibility checks."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .constants import SCHEMA_PATH
from .models import ConfirmedScanBundle


def validate_bundle_against_schema(
    bundle: ConfirmedScanBundle | dict[str, Any],
    schema_path: Path | None = None,
) -> list[str]:
    """Validate a Member 1 handoff bundle against schemas/salt_food_schema.json."""
    target = schema_path or SCHEMA_PATH
    schema = json.loads(target.read_text(encoding="utf-8"))
    payload = bundle.model_dump(mode="json") if isinstance(bundle, ConfirmedScanBundle) else bundle
    validator = Draft202012Validator(schema)
    return [err.message for err in validator.iter_errors(payload)]


def load_member2_verified_rules(source: Path) -> list[dict[str, Any]]:
    """Load Member 2's verified_rules.json or clinical_rules.csv cleanly."""
    suffix = source.suffix.lower()
    if suffix == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        return data.get("rules", data) if isinstance(data, dict) else data
    if suffix == ".csv":
        rows: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "rule_id": row["rule_id"].strip(),
                        "drug_class": row["drug_class"].strip(),
                        "active_salts": [s.strip() for s in row["active_salts"].split(";") if s.strip()],
                        "interfering_nutrients": [n.strip() for n in row["interfering_nutrients"].split(";") if n.strip()],
                        "culprit_indian_foods": [f.strip() for f in row["culprit_indian_foods"].split(";") if f.strip()],
                        "severity": row["severity"].strip().upper(),
                    }
                )
        return rows
    raise ValueError(f"Unsupported rules file: {source}")


def check_member2_rule_compatibility(
    bundle: ConfirmedScanBundle,
    member2_rules: list[dict[str, Any]],
) -> list[str]:
    """Verify Member 1's exported lookup keys trigger Member 2's matching rule IDs."""
    salts = [s.lower() for s in bundle.member2_lookup_keys.salt_names]
    food_labels = [lbl.lower() for lbl in bundle.member2_lookup_keys.member2_food_labels]
    matched_rule_ids: list[str] = []

    for rule in member2_rules:
        rule_salts = [s.lower() for s in rule.get("active_salts", [])]
        salt_hit = any(s in rs or rs in s for s in salts for rs in rule_salts)
        if not salt_hit:
            continue
        culprits = [c.lower() for c in rule.get("culprit_indian_foods", [])]
        food_hit = any(fl in c or c in fl for fl in food_labels for c in culprits)
        if food_hit:
            matched_rule_ids.append(rule["rule_id"])

    return matched_rule_ids
