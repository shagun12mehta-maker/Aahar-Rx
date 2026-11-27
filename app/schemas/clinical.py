"""
Aahar-Rx Clinical Schemas
Aligned 100% with data/verified_rules.json, DPDP Act 2023, and ANVESHAN Rule 3.
Updated with Medicine Box, Routine Alarms, and Doctor Video Consult Clash Reports.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

# Updated Clinical Disclaimer required by Blueprint
MANDATORY_CLINICAL_DISCLAIMER: str = (
    "Aahar-Rx provides timing and dietary guidance only. "
    "The app never advises skipping, altering, or replacing prescribed medication dosages. "
    "Any dose or medicine change is made only by a licensed doctor, through the Doctor Video Consult."
)

class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"

# -----------------------------------------------------------------------------
# Nested Sub-schemas matching data/verified_rules.json
# -----------------------------------------------------------------------------

class SafeTimeGapHours(BaseModel):
    before_food_hours: float = Field(..., description="Minimum hours to administer medication before meal")
    after_food_hours: float = Field(..., description="Minimum hours to wait after meal before taking medication")

class AbsorptionImpact(BaseModel):
    bioavailability_drop_pct: float = Field(..., description="Estimated percentage drop in bioavailability")
    t_max_delay_hours: float = Field(..., description="Delay in peak drug concentration (T_max) in hours")

class GharKiRasoiSwap(BaseModel):
    culprit: str = Field(..., description="Interfering culprit Indian food item")
    substitute: str = Field(..., description="Safe, culturally authentic household substitute")
    dietary_rationale: str = Field(..., description="Biochemical and physiological rationale for the swap")

class IFCTEvidence(BaseModel):
    food: str = Field(..., description="Food item name")
    ifct_code: str = Field(..., description="ICMR-NIN IFCT 2017 reference code")
    primary_nutrient: str = Field(..., description="Interfering nutrient component")
    value: str = Field(..., description="Nutrient concentration per serving/100g")
    clinical_note: str = Field(..., description="Clinical context of the nutrient interaction")

class Citation(BaseModel):
    source: str = Field(..., description="Citing authority (e.g., OpenFDA Drug Label, ICMR-NIN, Journal)")
    reference_id: str = Field(..., description="Monograph, NDA, DOI, or Table reference")

class ClinicalSignOff(BaseModel):
    reviewed: bool = Field(True, description="Whether rule was clinically vetted")
    reviewer_role: str = Field(..., description="Anonymous professional role of reviewer")
    status: str = Field("APPROVED", description="Approval status")

# -----------------------------------------------------------------------------
# Core Clinical Rule Schema
# -----------------------------------------------------------------------------

class ClinicalRule(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier (e.g., RULE-THY-001)")
    drug_class: str = Field(..., description="Pharmacological drug class")
    active_salts: List[str] = Field(..., description="Active pharmaceutical salts governed by this rule")
    interfering_nutrients: List[str] = Field(..., description="Interfering macro/micro nutrients")
    culprit_indian_foods: List[str] = Field(..., description="Common Indian food culprits")
    severity: SeverityLevel = Field(..., description="Interaction severity rating")
    interaction_type: str = Field(..., description="Pharmacokinetic or pharmacodynamic interaction type")
    biochemical_mechanism: str = Field(..., description="Detailed biochemical interaction pathway")
    ifct_evidence: List[IFCTEvidence] = Field(default_factory=list, description="Nutritional evidence from ICMR-NIN IFCT")
    safe_time_gap_hours: SafeTimeGapHours = Field(..., description="Recommended safe interval around meals")
    absorption_impact: AbsorptionImpact = Field(..., description="Absorption and pharmacokinetic impairment")
    ghar_ki_rasoi_swaps: List[GharKiRasoiSwap] = Field(default_factory=list, description="Practical kitchen swaps")
    citations: List[Citation] = Field(default_factory=list, description="Evidence citations")
    clinical_sign_off: ClinicalSignOff = Field(..., description="Governance verification metadata")

# -----------------------------------------------------------------------------
# Consent Schemas (DPDP Act 2023)
# -----------------------------------------------------------------------------

class ConsentRequest(BaseModel):
    purpose: str = Field(
        default="CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS",
        description="Specified purpose of processing under DPDP Act 2023"
    )
    consent_type: str = Field(
        default="PATIENT_PROCESSING",
        description="'PATIENT_PROCESSING' or 'DOCTOR_SHARE'"
    )
    data_elements: List[str] = Field(
        default_factory=lambda: ["PRESCRIPTION_SALTS", "MEAL_ITEMS"],
        description="Categories of clinical data to process"
    )

class ConsentResponse(BaseModel):
    consent_id: str = Field(..., description="Unique cryptographically secure DPDP consent identifier")
    consent_type: str = Field("PATIENT_PROCESSING", description="Type of consent granted")
    status: str = Field("ACTIVE", description="Status of consent (ACTIVE, REVOKED, EXPIRED)")
    valid_until: str = Field(..., description="ISO 8601 validity timestamp")
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# Scans Schemas (Member 1 OCR & Meal Detection)
# -----------------------------------------------------------------------------

class DetectedMedicine(BaseModel):
    medicine_name: str
    detected_salts: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    dosage_text_detected: Optional[str] = None

class DetectedMeal(BaseModel):
    meal_name: Optional[str] = "Meal"
    detected_food_items: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

class ScanPayload(BaseModel):
    consent_id: Optional[str] = Field(None, description="DPDP consent identifier (if passed in payload)")
    strip_ocr: Optional[DetectedMedicine] = None
    meal_detection: Optional[DetectedMeal] = None
    scan_timestamp: Optional[str] = None

class ScanResponse(BaseModel):
    scan_id: str
    status: str = "VALIDATED"
    detected_salts: List[str] = Field(default_factory=list)
    detected_food_items: List[str] = Field(default_factory=list)
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# Conflict Check Schemas
# -----------------------------------------------------------------------------

class ConflictCheckRequest(BaseModel):
    consent_id: Optional[str] = Field(None, description="DPDP consent identifier (if passed in payload)")
    active_salt: str = Field(..., description="Pharmaceutical active ingredient / salt")
    food_items: List[str] = Field(..., min_length=1, description="List of consumed or planned food items")

class ConflictDetail(BaseModel):
    rule_id: str
    drug_class: str
    severity: SeverityLevel
    matched_salt: str
    conflicted_foods: List[str]
    interaction_type: str
    biochemical_mechanism: str
    safe_time_gap_hours: SafeTimeGapHours
    absorption_impact: AbsorptionImpact
    ghar_ki_rasoi_swaps: List[GharKiRasoiSwap]
    ifct_evidence: List[IFCTEvidence]

class ConflictCheckResponse(BaseModel):
    has_conflict: bool
    active_salt: str
    conflicts: List[ConflictDetail] = Field(default_factory=list)
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# Timetable Generation Schemas
# -----------------------------------------------------------------------------

class TimetableMedicineInput(BaseModel):
    medicine_name: str
    active_salt: str
    prescribed_time: str = Field(..., description="Prescribed intake time in HH:MM format (24-hour)")

class TimetableMealInput(BaseModel):
    meal_name: str = Field(..., description="e.g. Breakfast, Lunch, Morning Chai, Dinner")
    planned_time: str = Field(..., description="Planned consumption time in HH:MM format (24-hour)")
    food_items: List[str] = Field(default_factory=list)

class TimetableRequest(BaseModel):
    consent_id: Optional[str] = Field(None, description="DPDP consent identifier (if passed in payload)")
    medications: List[TimetableMedicineInput] = Field(..., min_length=1)
    meals: List[TimetableMealInput] = Field(..., min_length=1)

class TimetableEntry(BaseModel):
    medicine_name: str
    active_salt: str
    prescribed_time: str
    calculated_safe_time: str
    timing_adjustment_reason: str
    conflicts_detected: List[str] = Field(default_factory=list)
    safe_time_gap_hours: Optional[SafeTimeGapHours] = None
    recommended_swaps: List[GharKiRasoiSwap] = Field(default_factory=list)

class TimetableResponse(BaseModel):
    total_medications: int
    timetable: List[TimetableEntry]
    summary_notes: List[str] = Field(default_factory=list)
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# NEW MODULE 1: Clash Report & Doctor Video Consult (WebRTC Jitsi)
# -----------------------------------------------------------------------------

class ClashReportRequest(BaseModel):
    active_salt: str = Field(..., description="High-risk salt triggering conflict")
    conflicted_food: str = Field(..., description="Indian food conflicting with drug")
    doctor_share_consent_id: Optional[str] = Field(
        None,
        description="Explicit DPDP consent authorizing health data sharing with consulting doctor"
    )

class ClashReportResponse(BaseModel):
    report_token: str = Field(..., description="Unique shareable token for doctor review")
    active_salt: str
    conflicted_food: str
    severity: str = "HIGH"
    biochemical_mechanism: str
    bioavailability_drop_pct: float
    recommended_swap: str
    jitsi_room_url: str = Field(..., description="Embeddable Jitsi Meet WebRTC room URL")
    anonymized_doctor_id: str = Field(..., description="Assigned anonymous physician identifier")
    created_at: str
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# NEW MODULE 2: Routine Shift Engine (Delayed Meal Alarm Adjustment)
# -----------------------------------------------------------------------------

class ShiftAlarmRequest(BaseModel):
    consent_id: Optional[str] = Field(None, description="DPDP consent identifier")
    medicine_name: str
    active_salt: str
    scheduled_time: str = Field(..., description="Original scheduled medicine time in HH:MM")
    meal_anchor: str = Field(..., description="Anchor meal, e.g. 'Breakfast', 'Morning Chai', 'Lunch'")
    delayed_meal_time: str = Field(..., description="Actual delayed meal time in HH:MM")

class ShiftAlarmResponse(BaseModel):
    medicine_name: str
    original_scheduled_time: str
    meal_anchor: str
    delayed_meal_time: str
    shifted_alarm_time: str = Field(..., description="New recalculated alarm time in HH:MM")
    shift_minutes: int = Field(..., description="Minutes shifted (+ for delay, - for advance)")
    shift_rationale: str
    fcm_payload: Dict[str, Any] = Field(default_factory=dict, description="Push notification payload")
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)

# -----------------------------------------------------------------------------
# NEW MODULE 3: Medicine Box (Stock & Expiry Tracking with 3-Day Alert)
# -----------------------------------------------------------------------------

class MedicineBoxItemCreate(BaseModel):
    brand: str = Field(..., description="Brand name on medicine box")
    salt: str = Field(..., description="Active pharmaceutical salt")
    expiry_date: str = Field(..., description="Expiry date in YYYY-MM-DD")
    initial_count: int = Field(..., ge=1, description="Initial total tablets/capsules")
    remaining_count: Optional[int] = Field(None, ge=0, description="Current remaining tablets")
    daily_dosage_count: int = Field(default=1, ge=1, description="Tablets consumed per day")

class ConsumeDoseRequest(BaseModel):
    doses_consumed: int = Field(default=1, ge=1, description="Number of tablets consumed")

class MedicineBoxItemResponse(BaseModel):
    item_id: str
    brand: str
    salt: str
    expiry_date: str
    initial_count: int
    remaining_count: int
    daily_dosage_count: int
    days_of_stock_left: int
    low_stock_alert: bool = Field(..., description="True if stock <= 3 days remaining")
    alert_message: Optional[str] = None
    reorder_url: Optional[str] = Field(None, description="1mg / PharmEasy search deep-link")
    is_expired: bool = False
    clinical_disclaimer: str = Field(default=MANDATORY_CLINICAL_DISCLAIMER)
