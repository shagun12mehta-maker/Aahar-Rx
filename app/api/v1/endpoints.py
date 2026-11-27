"""
Aahar-Rx API v1 Endpoints
Adheres strictly to GEMINI.md, DPDP Act 2023 Consent Guard, and ANVESHAN Rule 3.
Includes:
1. POST /api/v1/consent
2. POST /api/v1/scans
3. POST /api/v1/check-conflict
4. POST /api/v1/generate-timetable
5. POST /api/v1/clash-report (NEW: High-risk clash report + Jitsi WebRTC room)
6. POST /api/v1/shift-alarm (NEW: Dynamic routine meal shift alarm recalculation)
7. POST /api/v1/medicine-box (NEW: Inventory stock & expiry tracking)
8. POST /api/v1/medicine-box/{id}/consume (NEW: Dose consumption with 3-day low stock alert)
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.clinical import (
    ConsentRequest,
    ConsentResponse,
    ScanPayload,
    ScanResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    TimetableRequest,
    TimetableResponse,
    ClashReportRequest,
    ClashReportResponse,
    ShiftAlarmRequest,
    ShiftAlarmResponse,
    MedicineBoxItemCreate,
    ConsumeDoseRequest,
    MedicineBoxItemResponse,
    MedicineBoxListResponse,
    MANDATORY_CLINICAL_DISCLAIMER
)
from app.core.consent_guard import (
    verify_consent,
    verify_doctor_share_consent,
    ConsentRegistry
)
from app.services.conflict_engine import conflict_engine
from app.services.clash_consult_service import clash_consult_service
from app.services.routine_shift import routine_shift_engine
from app.services.medicine_box_service import medicine_box_service

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
    Supports 'PATIENT_PROCESSING' and 'DOCTOR_SHARE' consent types.
    """
    record = ConsentRegistry.register_consent(
        purpose=request.purpose,
        consent_type=request.consent_type
    )
    return ConsentResponse(
        consent_id=record["consent_id"],
        consent_type=record["consent_type"],
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
async def generate_patient_timetable(
    payload: TimetableRequest,
    consent_id: str = Depends(verify_consent)
) -> TimetableResponse:
    entries = conflict_engine.generate_safe_timetable(
        medications=payload.medications,
        meals=payload.meals
    )

    return TimetableResponse(
        total_medications=len(payload.medications),
        timetable=entries,
        summary_notes=[
            f"Calculated safe absorption windows for {len(payload.medications)} medication(s).",
            "Prescribed medicine dosages are strictly unaltered."
        ],
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 5. NEW MODULE: High-Risk Clash Report & Doctor Video Consult (WebRTC Jitsi)
# -----------------------------------------------------------------------------
@router.post(
    "/clash-report",
    response_model=ClashReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate shareable Clash Report & Jitsi Meet WebRTC room for High-Risk clashes"
)
async def generate_high_risk_clash_report(
    payload: ClashReportRequest,
    doctor_consent_id: str = Depends(verify_doctor_share_consent)
) -> ClashReportResponse:
    """
    Generates a shareable Clash Report token and provisioning an embeddable Jitsi Meet room.
    Requires separate explicit DPDP Act 2023 Doctor Data-Sharing Consent (doctor_share_consent_id).
    """
    report = clash_consult_service.generate_clash_report(
        active_salt=payload.active_salt,
        conflicted_food=payload.conflicted_food,
        doctor_consent_id=doctor_consent_id
    )

    return ClashReportResponse(
        report_token=report["report_token"],
        active_salt=report["active_salt"],
        conflicted_food=report["conflicted_food"],
        severity=report["severity"],
        biochemical_mechanism=report["biochemical_mechanism"],
        bioavailability_drop_pct=report["bioavailability_drop_pct"],
        recommended_swap=report["recommended_swap"],
        jitsi_room_url=report["jitsi_room_url"],
        anonymized_doctor_id=report["anonymized_doctor_id"],
        created_at=report["created_at"],
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )


@router.get(
    "/clash-report/{report_token}",
    response_model=ClashReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch pre-loaded Food-Medicine Clash Report for doctor view"
)
async def fetch_clash_report(
    report_token: str,
    doctor_consent_id: str = Depends(verify_doctor_share_consent)
) -> ClashReportResponse:
    report = clash_consult_service.get_report(report_token)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clash Report '{report_token}' not found."
        )
    if report.get("doctor_consent_id") != doctor_consent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor consent token mismatch for requested Clash Report."
        )
    return ClashReportResponse(
        report_token=report["report_token"],
        active_salt=report["active_salt"],
        conflicted_food=report["conflicted_food"],
        severity=report["severity"],
        biochemical_mechanism=report["biochemical_mechanism"],
        bioavailability_drop_pct=report["bioavailability_drop_pct"],
        recommended_swap=report["recommended_swap"],
        jitsi_room_url=report["jitsi_room_url"],
        anonymized_doctor_id=report["anonymized_doctor_id"],
        created_at=report["created_at"],
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 6. NEW MODULE: Routine Shift Engine (Delayed Meal Alarm Recalculation)
# -----------------------------------------------------------------------------
@router.post(
    "/shift-alarm",
    response_model=ShiftAlarmResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalculate and shift medication alarm when a meal routine is delayed"
)
async def shift_alarm_on_delayed_meal(
    payload: ShiftAlarmRequest,
    consent_id: str = Depends(verify_consent)
) -> ShiftAlarmResponse:
    """
    Extends the routine engine: when a meal is delayed (e.g. late breakfast),
    automatically recalculates and shifts dependent medication alarm times while preserving dosage.
    """
    shift_result = routine_shift_engine.shift_alarm_for_delayed_meal(
        medicine_name=payload.medicine_name,
        active_salt=payload.active_salt,
        scheduled_time=payload.scheduled_time,
        meal_anchor=payload.meal_anchor,
        delayed_meal_time=payload.delayed_meal_time
    )

    return ShiftAlarmResponse(
        medicine_name=shift_result["medicine_name"],
        original_scheduled_time=shift_result["original_scheduled_time"],
        meal_anchor=shift_result["meal_anchor"],
        delayed_meal_time=shift_result["delayed_meal_time"],
        shifted_alarm_time=shift_result["shifted_alarm_time"],
        shift_minutes=shift_result["shift_minutes"],
        shift_rationale=shift_result["shift_rationale"],
        fcm_payload=shift_result["fcm_payload"],
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

# -----------------------------------------------------------------------------
# 7. NEW MODULE: Medicine Box (Stock & Expiry Tracking with 3-Day Low Stock Alert)
# -----------------------------------------------------------------------------
@router.post(
    "/medicine-box",
    response_model=MedicineBoxItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register medication in digital Medicine Box with stock & expiry tracking"
)
async def add_medicine_to_box(
    payload: MedicineBoxItemCreate,
    consent_id: str = Depends(verify_consent)
) -> MedicineBoxItemResponse:
    item = medicine_box_service.add_medicine(
        brand=payload.brand,
        salt=payload.salt,
        expiry_date_str=payload.expiry_date,
        initial_count=payload.initial_count,
        remaining_count=payload.remaining_count,
        daily_dosage_count=payload.daily_dosage_count
    )

    return MedicineBoxItemResponse(
        **item,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )

@router.get(
    "/medicine-box",
    response_model=MedicineBoxListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all tracked medications in the digital Medicine Box"
)
async def list_medicine_box_items(
    consent_id: str = Depends(verify_consent)
) -> MedicineBoxListResponse:
    items = [
        MedicineBoxItemResponse(**item, clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER)
        for item in medicine_box_service.list_items()
    ]
    return MedicineBoxListResponse(
        total_items=len(items),
        items=items,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )


@router.post(
    "/medicine-box/{item_id}/consume",
    response_model=MedicineBoxItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Record dose consumption, calculate remaining days, and trigger 3-day low-stock alert"
)
async def consume_medicine_dose(
    item_id: str,
    payload: ConsumeDoseRequest = ConsumeDoseRequest(),
    consent_id: str = Depends(verify_consent)
) -> MedicineBoxItemResponse:
    item = medicine_box_service.consume_dose(item_id=item_id, doses=payload.doses_consumed)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine Box Item '{item_id}' not found."
        )

    return MedicineBoxItemResponse(
        **item,
        clinical_disclaimer=MANDATORY_CLINICAL_DISCLAIMER
    )
