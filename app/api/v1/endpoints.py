"""
Aahar-Rx API v1 Endpoints
Adheres strictly to GEMINI.md, DPDP Act 2023 Consent Guard, and ANVESHAN Rule 3.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status

from app.schemas.clinical import (
    ConsentRequest,
    ConsentResponse,
    ScanPayload,
    ScanResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    TimetableRequest,
    TimetableResponse,
    MANDATORY_CLINICAL_DISCLAIMER
)
from app.core.consent_guard import verify_consent, ConsentRegistry
from app.services.conflict_engine import conflict_engine

router = APIRouter(prefix="/api/v1", tags=["Aahar-Rx Clinical API"])

# -----------------------------------------------------------------------------
# 1. DPDP Act 2023 Consent Registration
# -----------------------------------------------------------------------------
@router.post(
    "/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create anonymous DPDP Act 2023 consent session"
)
async def create_consent_session(request: ConsentRequest = ConsentRequest()) -> ConsentResponse:
    """
    Creates an anonymous consent session fulfilling the Digital Personal Data Protection (DPDP) Act 2023.
    Returns a unique cryptographically secure consent_id valid for clinical interaction analysis.
    """
    record = ConsentRegistry.register_consent(purpose=request.purpose)
    return ConsentResponse(
        consent_id=record["consent_id"],
        status=record["status"],
        valid_until=record["valid_until"],
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 2. Member 1 Medicine Strip OCR & Meal Detection Payload Store
# -----------------------------------------------------------------------------
@router.post(
    "/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Store and validate medicine strip OCR & meal photo detection payload"
)
async def process_scan_payload(
    payload: ScanPayload,
    consent_id: str = Depends(verify_consent)
) -> ScanResponse:
    """
    Validates Member 1's medicine strip OCR and meal detection inputs under active consent.
    Extracts identified active pharmaceutical salts and Indian food culprits.
    """
    detected_salts: List[str] = []
    if payload.strip_ocr:
        detected_salts = payload.strip_ocr.detected_salts or [payload.strip_ocr.medicine_name]

    detected_food_items: List[str] = []
    if payload.meal_detection:
        detected_food_items = payload.meal_detection.detected_food_items

    scan_id = f"SCAN-{uuid.uuid4().hex[:8].upper()}"

    return ScanResponse(
        scan_id=scan_id,
        status="VALIDATED",
        detected_salts=detected_salts,
        detected_food_items=detected_food_items,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 3. Clinical Food-Drug Conflict Evaluation
# -----------------------------------------------------------------------------
@router.post(
    "/check-conflict",
    response_model=ConflictCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate active drug salt against Indian culinary foods"
)
async def check_food_drug_conflict(
    payload: ConflictCheckRequest,
    consent_id: str = Depends(verify_consent)
) -> ConflictCheckResponse:
    """
    Evaluates an active drug salt against Indian dietary items using data/verified_rules.json.
    Returns biochemical mechanisms, IFCT evidence, pharmacokinetic impact, and Ghar-Ki-Rasoi swaps.
    """
    conflicts = conflict_engine.evaluate_conflicts(
        active_salt=payload.active_salt,
        food_items=payload.food_items
    )

    return ConflictCheckResponse(
        has_conflict=len(conflicts) > 0,
        active_salt=payload.active_salt,
        conflicts=conflicts,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 4. Safe Daily Timetable Generator
# -----------------------------------------------------------------------------
@router.post(
    "/generate-timetable",
    response_model=TimetableResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalized safe medication and meal intake timetable"
)
async def generate_medication_timetable(
    payload: TimetableRequest,
    consent_id: str = Depends(verify_consent)
) -> TimetableResponse:
    """
    Calculates precise safe administration intervals between prescribed medications
    and planned meals using verified before_food_hours and after_food_hours windows.
    Never alters prescribed dosage.
    """
    timetable = conflict_engine.generate_safe_timetable(
        medications=payload.medications,
        meals=payload.meals
    )

    summary_notes = [
        "Timetable adheres to ICMR-NIN IFCT nutrient binding guidelines.",
        "Dosages remain strictly as ordered by prescribing clinician.",
        "Consult treating physician for any clinical symptom recurrence."
    ]

    return TimetableResponse(
        total_medications=len(timetable),
        timetable=timetable,
        summary_notes=summary_notes,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )
