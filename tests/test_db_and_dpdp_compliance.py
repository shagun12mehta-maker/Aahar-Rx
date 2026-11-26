"""Tests for relational DB seeding, DPDP Act 2023 consent/erasure, and ANVESHAN Rule 3 anonymity."""

from __future__ import annotations

from pathlib import Path
import re

from pydantic import ValidationError
import pytest

from aahar_backend.constants import CLINICAL_SAFETY_DISCLAIMER, PROJECT_ROOT
from aahar_backend.db import AaharDatabase, ConsentRequiredError, UserNotFoundError
from aahar_backend.models import (
    ConflictCheckRequest,
    ConsentCreateRequest,
    ScanIngestRequest,
    UserCreateRequest,
)


def test_db_seeds_all_8_verified_rules_salts_and_foods(tmp_path: Path) -> None:
    db = AaharDatabase(db_path=tmp_path / "test.db")
    rules = db.list_rules()
    salts = db.list_salts()
    foods = db.list_foods()

    assert len(rules) == 8
    assert {r["rule_id"] for r in rules} == {
        "RULE-THY-001",
        "RULE-IRO-002",
        "RULE-ANT-003",
        "RULE-BLD-004",
        "RULE-HTN-005",
        "RULE-DIA-006",
        "RULE-HYP-007",
        "RULE-LIP-008",
    }
    assert any(s["salt_name"] == "Levothyroxine Sodium" for s in salts)
    assert any(f["food_name"] == "Morning Masala Chai with Milk" for f in foods)


def test_dpdp_consent_enforcement_withdrawal_and_erasure(tmp_path: Path) -> None:
    db = AaharDatabase(db_path=tmp_path / "dpdp.db")
    user = db.create_user(UserCreateRequest(preferred_language="mr", age_band="elderly_60_plus"))

    # Refusing consent must be blocked
    with pytest.raises(ConsentRequiredError):
        db.record_consent(ConsentCreateRequest(user_id=user.user_id, consented=False))

    # Processing without active consent must fail
    with pytest.raises(ConsentRequiredError):
        db.require_active_consent(user.user_id, "dpdp_missing")

    consent = db.record_consent(ConsentCreateRequest(user_id=user.user_id, consented=True))
    assert consent.raw_images_stored is False

    # Ingest sanitized scan metadata
    scan = db.save_scan_metadata(
        ScanIngestRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            active_salts=["Levothyroxine Sodium"],
            confirmed_foods=["Morning Masala Chai with Milk"],
            meal_slot="early_morning_empty_stomach",
        )
    )
    assert scan.raw_images_stored is False

    # Withdrawing consent immediately blocks subsequent use
    db.withdraw_consent(consent.consent_id)
    with pytest.raises(ConsentRequiredError):
        db.require_active_consent(user.user_id, consent.consent_id)

    # Right to erasure purges scans/schedules and marks user erased
    erased = db.erase_user_data(user.user_id)
    assert erased.erased is True
    assert erased.scans_deleted == 1

    with pytest.raises(UserNotFoundError):
        db.record_consent(ConsentCreateRequest(user_id=user.user_id, consented=True))


def test_raw_image_fields_strictly_rejected_by_models() -> None:
    for bad_field in ("image_base64", "raw_image", "photo_base64", "meal_photo"):
        with pytest.raises(ValidationError):
            ScanIngestRequest(
                user_id="usr_1234",
                consent_id="dpdp_1234",
                active_salts=["Levothyroxine Sodium"],
                confirmed_foods=["Morning Masala Chai with Milk"],
                **{bad_field: "data:image/png;base64,AAAA"},
            )

    with pytest.raises(ValidationError):
        ConflictCheckRequest(
            user_id="usr_1234",
            consent_id="dpdp_1234",
            active_salts=["Warfarin Sodium"],
            food_items=["Palak Paneer"],
            image_bytes="forbidden",
        )


def test_clinical_safety_disclaimer_non_dosage_altering() -> None:
    lower = CLINICAL_SAFETY_DISCLAIMER.lower()
    assert "timing and dietary guidance only" in lower
    assert "never advises skipping" in lower
    assert "altering" in lower


def test_anveshan_rule3_strict_anonymity_across_all_deliverables() -> None:
    forbidden = [r"\bmustafa\b", r"\bmarjani\b", r"\bshagun\b", r"\bmehta\b"]
    for folder_name in ("src", "db", "docs", "scripts", "tests", "data"):
        folder = PROJECT_ROOT / folder_name
        for file_path in folder.rglob("*"):
            if not file_path.is_file() or file_path.suffix not in {".py", ".sql", ".md", ".json", ".csv"}:
                continue
            if file_path.resolve() == Path(__file__).resolve():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for pat in forbidden:
                assert not re.search(pat, text), f"Rule 3 anonymity failure ({pat}) in {file_path}"

    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    for pat in forbidden:
        assert not re.search(pat, readme_text), f"Rule 3 anonymity failure ({pat}) in README.md"
