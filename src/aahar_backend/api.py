"""FastAPI application for Aahar-Rx Member 4 (Backend, Safety & DPDP Compliance)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .conflict_engine import evaluate_conflicts
from .constants import CLINICAL_SAFETY_DISCLAIMER
from .db import AaharDatabase, ConsentRequiredError, UserNotFoundError
from .models import (
    ConflictCheckRequest,
    ConflictCheckResponse,
    ConsentCreateRequest,
    ConsentRecord,
    DataErasureResponse,
    PrivacyAuditSummary,
    QrHealthPassPayload,
    ScanIngestRequest,
    ScanRecordResponse,
    TimetableRequest,
    TimetableResponse,
    UserCreateRequest,
    UserProfile,
)
from .timetable_engine import generate_safe_timetable


def create_app(
    db: AaharDatabase | None = None,
    db_path: Path | str | None = None,
) -> FastAPI:
    """Create the production FastAPI app wired to SQLite/Supabase repository and Member 2 rules."""
    database = db or AaharDatabase(db_path=db_path)

    app = FastAPI(
        title="Aahar-Rx Backend & Safety API (Member 4)",
        version="1.0.0",
        description=(
            "Food-drug interaction engine, safe time-gap timetable generator, "
            "QR Health Pass payload API, and DPDP Act 2023 consent/erasure controls. "
            f"{CLINICAL_SAFETY_DISCLAIMER}"
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["System"])
    def health() -> dict[str, Any]:
        audit = database.get_privacy_audit_summary()
        return {
            "status": "ok",
            "module": "aahar-rx-member4-backend-safety",
            "verified_rules_loaded": audit.verified_rules_loaded,
            "dpdp_compliant": audit.dpdp_compliant,
            "anonymity_rule3_enforced": audit.anonymity_rule3_enforced,
            "safety_disclaimer": CLINICAL_SAFETY_DISCLAIMER,
        }

    # --- Users & DPDP Act 2023 Consent / Erasure ---
    @app.post("/api/v1/users", response_model=UserProfile, tags=["DPDP Privacy & Users"])
    def create_user(req: UserCreateRequest) -> UserProfile:
        return database.create_user(req)

    @app.post("/api/v1/consent", response_model=ConsentRecord, tags=["DPDP Privacy & Users"])
    def capture_consent(req: ConsentCreateRequest) -> ConsentRecord:
        try:
            return database.record_consent(req)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/v1/consent/{consent_id}", response_model=ConsentRecord, tags=["DPDP Privacy & Users"])
    def get_consent(consent_id: str) -> ConsentRecord:
        try:
            return database.get_consent(consent_id)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/v1/consent/{consent_id}/withdraw",
        response_model=ConsentRecord,
        tags=["DPDP Privacy & Users"],
    )
    def withdraw_consent(consent_id: str) -> ConsentRecord:
        try:
            return database.withdraw_consent(consent_id)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete(
        "/api/v1/users/{user_id}/data",
        response_model=DataErasureResponse,
        tags=["DPDP Privacy & Users"],
    )
    def erase_user_data(user_id: str) -> DataErasureResponse:
        try:
            return database.erase_user_data(user_id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/v1/privacy/audit-summary", response_model=PrivacyAuditSummary, tags=["DPDP Privacy & Users"])
    def privacy_audit_summary() -> PrivacyAuditSummary:
        return database.get_privacy_audit_summary()

    # --- Reference Clinical Data (Seeded from Member 2 verified_rules.json) ---
    @app.get("/api/v1/rules", tags=["Clinical Reference"])
    def list_rules() -> list[dict[str, Any]]:
        return database.list_rules()

    @app.get("/api/v1/salts", tags=["Clinical Reference"])
    def list_salts() -> list[dict[str, Any]]:
        return database.list_salts()

    @app.get("/api/v1/foods", tags=["Clinical Reference"])
    def list_foods() -> list[dict[str, Any]]:
        return database.list_foods()

    # --- Member 1 Scan Metadata Ingestion (No Raw Images) ---
    @app.post("/api/v1/scans/ingest", response_model=ScanRecordResponse, tags=["Smart Scan Ingestion"])
    def ingest_scan_metadata(req: ScanIngestRequest) -> ScanRecordResponse:
        try:
            return database.save_scan_metadata(req)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    # --- Core Conflict & Safe Time-Gap Timetable APIs ---
    @app.post("/api/v1/check-conflict", response_model=ConflictCheckResponse, tags=["Clinical Engine"])
    def check_conflict(req: ConflictCheckRequest) -> ConflictCheckResponse:
        try:
            database.require_active_consent(req.user_id, req.consent_id)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        rules = database.list_rules()
        matches = evaluate_conflicts(
            active_salts=req.active_salts,
            food_items=req.food_items,
            rules=rules,
            nutrient_flags=req.nutrient_flags,
            dose_time_hhmm=req.dose_time_hhmm,
        )
        highest: str = "NONE"
        if matches:
            highest = matches[0].severity
        return ConflictCheckResponse(
            user_id=req.user_id,
            consent_id=req.consent_id,
            checked_salts=req.active_salts,
            checked_foods=req.food_items,
            has_conflicts=bool(matches),
            highest_severity=highest,  # type: ignore[arg-type]
            conflicts=matches,
        )

    @app.post("/api/v1/generate-timetable", response_model=TimetableResponse, tags=["Clinical Engine"])
    def generate_timetable(req: TimetableRequest) -> TimetableResponse:
        try:
            database.require_active_consent(req.user_id, req.consent_id)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        rules = database.list_rules()
        result = generate_safe_timetable(
            user_id=req.user_id,
            consent_id=req.consent_id,
            medications=req.medications,
            meals=req.meals,
            rules=rules,
        )
        database.save_schedule(
            response=result,
            medications=[m.model_dump(mode="json") for m in req.medications],
            meals=[ml.model_dump(mode="json") for ml in req.meals],
        )
        return result

    @app.get("/api/v1/schedules/{schedule_id}", tags=["Member 3 Frontend & QR"])
    def get_schedule(schedule_id: str) -> dict[str, Any]:
        try:
            return database.get_schedule(schedule_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/v1/health-pass/{schedule_id}",
        response_model=QrHealthPassPayload,
        tags=["Member 3 Frontend & QR"],
    )
    def get_qr_health_pass(schedule_id: str) -> QrHealthPassPayload:
        try:
            sched = database.get_schedule(schedule_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return QrHealthPassPayload.model_validate(sched["qr_health_pass"])

    return app


app = create_app()
