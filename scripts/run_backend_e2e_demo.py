"""Day 6/7 End-to-End Backend Demo Runner across all 4 Indian patient scenarios."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aahar_backend.api import create_app  # noqa: E402
from aahar_backend.db import AaharDatabase  # noqa: E402
from aahar_backend.models import (  # noqa: E402
    ConflictCheckRequest,
    ConsentCreateRequest,
    MealSlotInput,
    MedicationDoseInput,
    ScanIngestRequest,
    TimetableRequest,
    UserCreateRequest,
)


def _find_endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise KeyError(f"Route {method} {path} not found")


def main() -> None:
    db = AaharDatabase(db_path=":memory:")
    app = create_app(db=db)

    create_user = _find_endpoint(app, "/api/v1/users", "POST")
    capture_consent = _find_endpoint(app, "/api/v1/consent", "POST")
    ingest_scan = _find_endpoint(app, "/api/v1/scans/ingest", "POST")
    check_conflict = _find_endpoint(app, "/api/v1/check-conflict", "POST")
    gen_timetable = _find_endpoint(app, "/api/v1/generate-timetable", "POST")
    get_qr = _find_endpoint(app, "/api/v1/health-pass/{schedule_id}", "GET")
    audit_ep = _find_endpoint(app, "/api/v1/privacy/audit-summary", "GET")
    erase_ep = _find_endpoint(app, "/api/v1/users/{user_id}/data", "DELETE")

    user = create_user(UserCreateRequest(preferred_language="hi", age_band="elderly_60_plus"))
    consent = capture_consent(ConsentCreateRequest(user_id=user.user_id, consented=True))
    print(f"[1] Created pseudonymous user {user.user_id} with DPDP consent {consent.consent_id}")

    scan = ingest_scan(
        ScanIngestRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            active_salts=["Levothyroxine Sodium", "Ferrous Ascorbate"],
            confirmed_foods=["Morning Masala Chai with Milk", "Palak Paneer"],
            nutrient_flags=["calcium", "tannins_polyphenols"],
            meal_slot="early_morning_empty_stomach",
        )
    )
    print(f"[2] Ingested scan metadata {scan.scan_id} (raw_images_stored={scan.raw_images_stored})")

    scenarios = [
        ("Scenario 1: Thyroid + Milky Chai", ["Levothyroxine Sodium"], ["Morning Masala Chai with Milk"], "07:00"),
        ("Scenario 2: Iron + Palak Paneer & Chai", ["Ferrous Ascorbate"], ["Palak Paneer", "Masala Chai"], "13:00"),
        ("Scenario 3: Telmisartan + Sendha Namak & Coconut Water", ["Telmisartan"], ["Sendha Namak (Rock Salt / Low Sodium Salt)", "Tender Coconut Water (multiple glasses)"], "09:00"),
        ("Scenario 4: Warfarin + Sarson ka Saag", ["Warfarin Sodium"], ["Sarson ka Saag", "Green Coriander & Mint Chutney"], "20:00"),
    ]
    print("\n[3] Running /check-conflict across Member 2's 4 patient personas:")
    for label, salts, foods, dose_t in scenarios:
        res = check_conflict(
            ConflictCheckRequest(
                user_id=user.user_id,
                consent_id=consent.consent_id,
                active_salts=salts,
                food_items=foods,
                dose_time_hhmm=dose_t,
            )
        )
        top = res.conflicts[0]
        print(f"  - {label} -> {top.rule_id} [{top.severity}] | Swap: {top.ghar_ki_rasoi_swaps[0].substitute}")

    tt = gen_timetable(
        TimetableRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            medications=[
                MedicationDoseInput(medicine_label="Thyronorm", active_salt="Levothyroxine Sodium", preferred_time_hhmm="06:30"),
                MedicationDoseInput(medicine_label="Orofer XT", active_salt="Ferrous Ascorbate", preferred_time_hhmm="13:15"),
                MedicationDoseInput(medicine_label="Glycomet", active_salt="Metformin Hydrochloride", preferred_time_hhmm="20:00"),
            ],
            meals=[
                MealSlotInput(meal_slot="early_morning_empty_stomach", time_hhmm="07:00", food_items=["Morning Masala Chai with Milk"]),
                MealSlotInput(meal_slot="lunch", time_hhmm="13:00", food_items=["Palak Paneer", "Masala Chai"]),
                MealSlotInput(meal_slot="dinner", time_hhmm="20:30", food_items=["Gulab Jamun / Jalebi"]),
            ],
        )
    )
    print(f"\n[4] Generated Timetable {tt.schedule_id} ({tt.conflict_count} conflicts resolved):")
    for entry in tt.timeline:
        print(f"  * {entry.recommended_time_hhmm} [{entry.status}] {entry.label} -> {entry.guidance}")

    qr = get_qr(tt.schedule_id)
    print(f"\n[5] QR Health Pass active_salts={qr.active_salts}, swaps={len(qr.key_kitchen_swaps)}")
    print("[6] Privacy Audit Summary:", json.dumps(audit_ep().model_dump(), indent=2))
    erased = erase_ep(user.user_id)
    print("[7] DPDP Right to Erasure:", erased.model_dump())


if __name__ == "__main__":
    main()
