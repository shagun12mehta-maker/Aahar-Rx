"""Tests for Member 2 rule compatibility, schema validation, DPDP pre-scan consent, and Rule 3 anonymity."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from aahar_scan.constants import CLINICAL_SAFETY_DISCLAIMER, DATA_DIR, PROJECT_ROOT
from aahar_scan.meal_vision import MealVisionService
from aahar_scan.member2_handoff import (
    check_member2_rule_compatibility,
    load_member2_verified_rules,
    validate_bundle_against_schema,
)
from aahar_scan.models import MealConfirmationUpdate
from aahar_scan.pipeline import (
    AaharSmartScanPipeline,
    ConsentRequiredError,
    create_scan_consent,
)
from fixtures.generate_test_assets import generate_meal_image_bytes, generate_strip_image_bytes


def test_dpdp_pre_scan_consent_and_ephemeral_retention() -> None:
    with pytest.raises(ConsentRequiredError):
        create_scan_consent(False)

    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    strip_bytes = generate_strip_image_bytes("01_thyronorm_clean")
    meal_bytes = generate_meal_image_bytes("thali_palak_dal_curd")

    with pytest.raises(ConsentRequiredError):
        pipeline.scan_medicine_strip(strip_bytes, consent=None)

    with pytest.raises(ConsentRequiredError):
        pipeline.scan_meal_photo(meal_bytes, consent=None)

    consent = create_scan_consent(True)
    assert consent.raw_images_retained is False
    assert consent.retention_policy == "ephemeral_in_memory"


def test_clinical_safety_disclaimer_wording_and_presence() -> None:
    lower = CLINICAL_SAFETY_DISCLAIMER.lower()
    assert "timing and dietary guidance only" in lower
    assert "never advises skipping" in lower
    assert "altering" in lower

    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    consent = create_scan_consent(True)
    strip_res = pipeline.scan_medicine_strip(generate_strip_image_bytes("01_thyronorm_clean"), consent)
    meal_res = pipeline.scan_meal_photo(generate_meal_image_bytes("thali_palak_dal_curd"), consent)
    assert strip_res.safety_disclaimer == CLINICAL_SAFETY_DISCLAIMER
    assert meal_res.safety_disclaimer == CLINICAL_SAFETY_DISCLAIMER

    pipeline.confirm_meal(meal_res.session_id, MealConfirmationUpdate())
    bundle = pipeline.export_handoff_bundle(
        consent=consent,
        meal_session_id=meal_res.session_id,
        medications=strip_res.resolved_medications,
        preferred_language="mr",
    )
    assert bundle.safety_disclaimer == CLINICAL_SAFETY_DISCLAIMER
    assert validate_bundle_against_schema(bundle) == []


def test_member1_brand_directory_covers_all_member2_salts() -> None:
    raw_rules = load_member2_verified_rules(DATA_DIR / "verified_rules.json")
    csv_rules = load_member2_verified_rules(DATA_DIR / "clinical_rules.csv")
    assert len(raw_rules) == 8
    assert len(csv_rules) == 8

    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    all_member1_salts = {
        salt.lower()
        for entry in pipeline.salt_resolver.entries
        for salt in entry["active_salts"]
    }
    for rule in raw_rules:
        for req_salt in rule["active_salts"]:
            req_l = req_salt.lower()
            assert any(
                req_l in m_salt or m_salt in req_l for m_salt in all_member1_salts
            ), f"Member 2 salt '{req_salt}' ({rule['rule_id']}) missing from Member 1 brand directory"


@pytest.mark.parametrize(
    ("brand_id", "food_id", "meal_slot", "expected_rule_id"),
    [
        ("thyronorm", "chai_with_milk", "early_morning_empty_stomach", "RULE-THY-001"),
        ("orofer_xt", "palak_spinach", "lunch", "RULE-IRO-002"),
        ("ciplox", "buttermilk_chaas", "lunch", "RULE-ANT-003"),
        ("warf", "sarson_ka_saag", "dinner", "RULE-BLD-004"),
        ("amlong", "mosambi_sweet_lime_juice", "breakfast", "RULE-HTN-005"),
        ("glycomet", "gulab_jamun_sweets", "dinner", "RULE-DIA-006"),
        ("telma", "tender_coconut_water", "mid_morning", "RULE-HYP-007"),
        ("atorva", "samosa_fried", "evening_chai_snack", "RULE-LIP-008"),
    ],
)
def test_member1_handoff_triggers_all_8_member2_rules(
    brand_id: str,
    food_id: str,
    meal_slot: str,
    expected_rule_id: str,
) -> None:
    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    consent = create_scan_consent(True)
    med = pipeline.select_manual_medicine(brand_id, intended_dose_time_hhmm="07:00")
    meal = pipeline.scan_meal_photo(
        generate_meal_image_bytes("thali_palak_dal_curd"),
        consent,
        meal_slot=meal_slot,  # type: ignore[arg-type]
    )
    pipeline.confirm_meal(
        meal.session_id,
        MealConfirmationUpdate(confirm_food_ids=[], add_food_ids=[food_id]),
    )
    bundle = pipeline.export_handoff_bundle(
        consent=consent,
        meal_session_id=meal.session_id,
        medications=[med],
    )
    assert validate_bundle_against_schema(bundle) == []

    rules = load_member2_verified_rules(DATA_DIR / "verified_rules.json")
    matched_ids = check_member2_rule_compatibility(bundle, rules)
    assert expected_rule_id in matched_ids


def test_anveshan_rule3_strict_anonymity_across_project() -> None:
    forbidden_patterns = [r"\bmustafa\b", r"\bmarjani\b", r"\bshagun\b", r"\bmehta\b"]
    for folder_name in ("src", "schemas", "data", "docs", "scripts", "tests"):
        folder = PROJECT_ROOT / folder_name
        for file_path in folder.rglob("*"):
            if not file_path.is_file() or file_path.suffix not in {".py", ".json", ".md", ".csv"}:
                continue
            if file_path.resolve() == Path(__file__).resolve():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for pat in forbidden_patterns:
                assert not re.search(pat, text), f"Anonymity violation ({pat}) in {file_path}"

    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8", errors="ignore").lower()
    for pat in forbidden_patterns:
        assert not re.search(pat, readme_text), f"Anonymity violation ({pat}) in README.md"
