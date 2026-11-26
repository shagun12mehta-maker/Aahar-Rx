"""Tests for conflict detection across all 8 Member 2 rules, PK curves, and timetable generation."""

from __future__ import annotations

import pytest

from aahar_backend.conflict_engine import build_pharmacokinetic_curve, evaluate_conflicts
from aahar_backend.db import AaharDatabase
from aahar_backend.models import (
    ConsentCreateRequest,
    MealSlotInput,
    MedicationDoseInput,
    UserCreateRequest,
)
from aahar_backend.timetable_engine import generate_safe_timetable


@pytest.mark.parametrize(
    ("salt", "food", "expected_rule_id", "expected_severity"),
    [
        ("Levothyroxine Sodium", "Morning Masala Chai with Milk", "RULE-THY-001", "HIGH"),
        ("Ferrous Ascorbate", "Palak Paneer", "RULE-IRO-002", "HIGH"),
        ("Ciprofloxacin", "Chaas / Buttermilk", "RULE-ANT-003", "HIGH"),
        ("Warfarin Sodium", "Sarson ka Saag", "RULE-BLD-004", "HIGH"),
        ("Amlodipine", "Mosambi (Sweet Lime) Juice in large volume", "RULE-HTN-005", "MODERATE"),
        ("Metformin Hydrochloride", "Gulab Jamun / Jalebi", "RULE-DIA-006", "MODERATE"),
        ("Telmisartan", "Sendha Namak (Rock Salt / Low Sodium Salt)", "RULE-HYP-007", "MODERATE"),
        ("Atorvastatin", "Deep-fried pakoras / Poori (High Re-heated Vanaspati)", "RULE-LIP-008", "MODERATE"),
    ],
)
def test_conflict_engine_covers_all_8_verified_rules(
    salt: str,
    food: str,
    expected_rule_id: str,
    expected_severity: str,
) -> None:
    db = AaharDatabase(db_path=":memory:")
    rules = db.list_rules()
    matches = evaluate_conflicts(
        active_salts=[salt],
        food_items=[food],
        rules=rules,
        dose_time_hhmm="07:00",
    )
    assert any(m.rule_id == expected_rule_id for m in matches)
    hit = next(m for m in matches if m.rule_id == expected_rule_id)
    assert hit.severity == expected_severity
    assert len(hit.ghar_ki_rasoi_swaps) >= 1
    assert len(hit.absorption_curve) == 17


def test_conflict_engine_handles_member1_canonical_food_ids_and_nutrients() -> None:
    db = AaharDatabase(db_path=":memory:")
    rules = db.list_rules()

    matches = evaluate_conflicts(
        active_salts=["Levothyroxine Sodium"],
        food_items=["chai_with_milk"],
        nutrient_flags=["calcium", "tannins_polyphenols"],
        rules=rules,
        dose_time_hhmm="06:30",
    )
    assert matches[0].rule_id == "RULE-THY-001"
    assert matches[0].recommended_earliest_meal_time == "07:30"


def test_pharmacokinetic_curve_direction_for_drop_vs_cyp3a4_elevation() -> None:
    # Iron + Chai: +62% bioavailability drop -> lower interfered peak
    drop_curve = build_pharmacokinetic_curve(bioavailability_drop_pct=62.0, t_max_delay_hours=2.0)
    max_norm = max(p.normal_efficacy_pct for p in drop_curve)
    max_int = max(p.interfered_efficacy_pct for p in drop_curve)
    assert max_int < max_norm

    # Amlodipine + Grapefruit: -45% drop (excess exposure) -> higher interfered peak
    cyp_curve = build_pharmacokinetic_curve(bioavailability_drop_pct=-45.0, t_max_delay_hours=0.5)
    max_cyp = max(p.interfered_efficacy_pct for p in cyp_curve)
    assert max_cyp > max_norm


def test_multi_drug_safe_timetable_generation_and_qr_pass() -> None:
    db = AaharDatabase(db_path=":memory:")
    user = db.create_user(UserCreateRequest(preferred_language="hi"))
    consent = db.record_consent(ConsentCreateRequest(user_id=user.user_id, consented=True))
    rules = db.list_rules()

    tt = generate_safe_timetable(
        user_id=user.user_id,
        consent_id=consent.consent_id,
        medications=[
            MedicationDoseInput(medicine_label="Thyronorm", active_salt="Levothyroxine Sodium", preferred_time_hhmm="06:30"),
            MedicationDoseInput(medicine_label="Orofer XT", active_salt="Ferrous Ascorbate", preferred_time_hhmm="13:15"),
            MedicationDoseInput(medicine_label="Glycomet", active_salt="Metformin Hydrochloride", preferred_time_hhmm="20:00"),
            MedicationDoseInput(medicine_label="Warf", active_salt="Warfarin Sodium", preferred_time_hhmm="21:30"),
        ],
        meals=[
            MealSlotInput(meal_slot="early_morning_empty_stomach", time_hhmm="07:00", food_items=["Morning Masala Chai with Milk"]),
            MealSlotInput(meal_slot="lunch", time_hhmm="13:00", food_items=["Palak Paneer", "Masala Chai"]),
            MealSlotInput(meal_slot="dinner", time_hhmm="20:30", food_items=["Sarson ka Saag", "Gulab Jamun / Jalebi"]),
        ],
        rules=rules,
    )

    assert tt.conflict_count >= 4
    chai_slot = next(e for e in tt.timeline if "early_morning_empty_stomach" in e.label)
    assert chai_slot.recommended_time_hhmm == "07:30"
    assert chai_slot.status == "shifted_for_safe_gap"

    iron_slot = next(e for e in tt.timeline if "Orofer XT" in e.label)
    assert iron_slot.recommended_time_hhmm == "15:00"
    assert iron_slot.status == "shifted_for_safe_gap"

    met_slot = next(e for e in tt.timeline if "Glycomet" in e.label)
    assert met_slot.status == "take_with_meal_buffer"
    assert met_slot.recommended_time_hhmm == "20:36"

    warf_slot = next(e for e in tt.timeline if "Warf" in e.label)
    assert warf_slot.status == "consistency_advisory"

    # QR Health Pass contains zero user_id/PII and summarizes active salts
    qr_json = tt.qr_health_pass.model_dump()
    assert "user_id" not in qr_json
    assert len(qr_json["active_salts"]) == 4
    assert len(qr_json["key_kitchen_swaps"]) >= 1
