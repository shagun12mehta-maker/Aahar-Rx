"""End-to-end backend API contract & OpenAPI tests for Member 4 FastAPI endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
import pytest

from aahar_backend.api import create_app
from aahar_backend.db import AaharDatabase
from aahar_backend.models import (
    ConflictCheckRequest,
    ConsentCreateRequest,
    MealSlotInput,
    MedicationDoseInput,
    ScanIngestRequest,
    TimetableRequest,
    UserCreateRequest,
)


def _endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise KeyError(f"Missing endpoint {method} {path}")


def test_end_to_end_backend_api_lifecycle(tmp_path: Path) -> None:
    db = AaharDatabase(db_path=tmp_path / "e2e.db")
    app = create_app(db=db)

    # OpenAPI schema builds cleanly with all expected paths
    openapi = app.openapi()
    for path in (
        "/health",
        "/api/v1/users",
        "/api/v1/consent",
        "/api/v1/consent/{consent_id}/withdraw",
        "/api/v1/users/{user_id}/data",
        "/api/v1/rules",
        "/api/v1/salts",
        "/api/v1/foods",
        "/api/v1/scans/ingest",
        "/api/v1/check-conflict",
        "/api/v1/generate-timetable",
        "/api/v1/schedules/{schedule_id}",
        "/api/v1/health-pass/{schedule_id}",
        "/api/v1/privacy/audit-summary",
    ):
        assert path in openapi["paths"]

    health = _endpoint(app, "/health", "GET")()
    assert health["status"] == "ok"
    assert health["verified_rules_loaded"] == 8
    assert health["dpdp_compliant"] is True

    # Reference endpoints
    assert len(_endpoint(app, "/api/v1/rules", "GET")()) == 8
    assert len(_endpoint(app, "/api/v1/salts", "GET")()) >= 12
    assert len(_endpoint(app, "/api/v1/foods", "GET")()) >= 15

    # User + Consent gates
    user = _endpoint(app, "/api/v1/users", "POST")(UserCreateRequest(preferred_language="hi"))
    with pytest.raises(HTTPException) as bad_consent:
        _endpoint(app, "/api/v1/consent", "POST")(
            ConsentCreateRequest(user_id=user.user_id, consented=False)
        )
    assert bad_consent.value.status_code == 403

    with pytest.raises(HTTPException) as blocked_conflict:
        _endpoint(app, "/api/v1/check-conflict", "POST")(
            ConflictCheckRequest(
                user_id=user.user_id,
                consent_id="dpdp_invalid",
                active_salts=["Levothyroxine Sodium"],
                food_items=["Morning Masala Chai with Milk"],
            )
        )
    assert blocked_conflict.value.status_code == 403

    consent = _endpoint(app, "/api/v1/consent", "POST")(
        ConsentCreateRequest(user_id=user.user_id, consented=True)
    )

    # Scan ingest
    scan = _endpoint(app, "/api/v1/scans/ingest", "POST")(
        ScanIngestRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            active_salts=["Levothyroxine Sodium"],
            confirmed_foods=["Morning Masala Chai with Milk"],
            nutrient_flags=["calcium", "tannins_polyphenols"],
            meal_slot="early_morning_empty_stomach",
        )
    )
    assert scan.raw_images_stored is False

    # Check conflict
    conflict_res = _endpoint(app, "/api/v1/check-conflict", "POST")(
        ConflictCheckRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            active_salts=["Levothyroxine Sodium"],
            food_items=["Morning Masala Chai with Milk"],
            dose_time_hhmm="07:00",
        )
    )
    assert conflict_res.has_conflicts is True
    assert conflict_res.highest_severity == "HIGH"
    assert conflict_res.conflicts[0].recommended_earliest_meal_time == "08:00"

    # Generate & retrieve timetable + QR Health Pass
    tt = _endpoint(app, "/api/v1/generate-timetable", "POST")(
        TimetableRequest(
            user_id=user.user_id,
            consent_id=consent.consent_id,
            medications=[
                MedicationDoseInput(
                    medicine_label="Thyronorm",
                    active_salt="Levothyroxine Sodium",
                    preferred_time_hhmm="07:00",
                )
            ],
            meals=[
                MealSlotInput(
                    meal_slot="early_morning_empty_stomach",
                    time_hhmm="07:15",
                    food_items=["Morning Masala Chai with Milk"],
                )
            ],
        )
    )
    saved = _endpoint(app, "/api/v1/schedules/{schedule_id}", "GET")(tt.schedule_id)
    assert saved["schedule_id"] == tt.schedule_id

    qr = _endpoint(app, "/api/v1/health-pass/{schedule_id}", "GET")(tt.schedule_id)
    assert qr.schedule_id == tt.schedule_id

    audit = _endpoint(app, "/api/v1/privacy/audit-summary", "GET")()
    assert audit.raw_images_stored_count == 0
    assert audit.stored_scans_count == 1
    assert audit.stored_schedules_count == 1

    # Erase user data -> subsequent schedule check / conflict check blocked
    erased = _endpoint(app, "/api/v1/users/{user_id}/data", "DELETE")(user.user_id)
    assert erased.erased is True
    assert erased.scans_deleted == 1
    assert erased.schedules_deleted == 1

    with pytest.raises(HTTPException) as after_erase:
        _endpoint(app, "/api/v1/check-conflict", "POST")(
            ConflictCheckRequest(
                user_id=user.user_id,
                consent_id=consent.consent_id,
                active_salts=["Levothyroxine Sodium"],
                food_items=["Morning Masala Chai with Milk"],
            )
        )
    assert after_erase.value.status_code == 403
