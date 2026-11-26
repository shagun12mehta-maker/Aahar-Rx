"""Strict Pydantic v2 schemas for Aahar-Rx Backend, DPDP Consent, Conflict & Timetable APIs."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import CLINICAL_SAFETY_DISCLAIMER, DPDP_DEFAULT_PURPOSE, FORBIDDEN_RAW_IMAGE_FIELDS

LanguageCode = Literal["en", "hi", "mr"]
MealSlotName = Literal[
    "early_morning_empty_stomach",
    "breakfast",
    "mid_morning",
    "lunch",
    "evening_chai_snack",
    "dinner",
    "bedtime",
]


class StrictNoRawImageModel(BaseModel):
    """Base request model enforcing DPDP data minimization (rejects raw image blobs)."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _reject_raw_images(cls, data: Any) -> Any:
        if isinstance(data, dict):
            bad_keys = sorted(set(data.keys()) & FORBIDDEN_RAW_IMAGE_FIELDS)
            if bad_keys:
                raise ValueError(
                    f"DPDP Act 2023 policy violation: raw image fields are prohibited ({bad_keys})."
                )
        return data


class UserCreateRequest(StrictNoRawImageModel):
    preferred_language: LanguageCode = "en"
    age_band: Literal["adult", "elderly_60_plus", "antenatal"] = "adult"


class UserProfile(BaseModel):
    user_id: str
    preferred_language: LanguageCode
    age_band: str
    created_at_utc: str


class ConsentCreateRequest(StrictNoRawImageModel):
    user_id: str = Field(min_length=4)
    consented: bool
    purpose: str = Field(default=DPDP_DEFAULT_PURPOSE, min_length=8)
    retention_policy: Literal["minimal_metadata_no_raw_images", "ephemeral_session_only"] = (
        "minimal_metadata_no_raw_images"
    )


class ConsentRecord(BaseModel):
    consent_id: str
    user_id: str
    consented: bool
    purpose: str
    retention_policy: str
    raw_images_stored: Literal[False] = False
    granted_at_utc: str
    withdrawn_at_utc: str | None = None


class ScanIngestRequest(StrictNoRawImageModel):
    """Sanitized handoff payload from Member 1 Smart Scan (salts + confirmed foods only)."""

    user_id: str = Field(min_length=4)
    consent_id: str = Field(min_length=4)
    active_salts: list[str] = Field(min_length=1)
    confirmed_foods: list[str] = Field(min_length=1)
    nutrient_flags: list[str] = Field(default_factory=list)
    meal_slot: MealSlotName = "lunch"
    confirmed_by_user: Literal[True] = True


class ScanRecordResponse(BaseModel):
    scan_id: str
    user_id: str
    consent_id: str
    active_salts: list[str]
    confirmed_foods: list[str]
    nutrient_flags: list[str]
    meal_slot: MealSlotName
    raw_images_stored: Literal[False] = False
    created_at_utc: str


class ConflictCheckRequest(StrictNoRawImageModel):
    user_id: str = Field(min_length=4)
    consent_id: str = Field(min_length=4)
    active_salts: list[str] = Field(min_length=1)
    food_items: list[str] = Field(min_length=1)
    nutrient_flags: list[str] = Field(default_factory=list)
    dose_time_hhmm: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class AbsorptionCurvePoint(BaseModel):
    time_hours: float
    normal_efficacy_pct: float
    interfered_efficacy_pct: float


class GharKiRasoiSwap(BaseModel):
    culprit: str
    substitute: str
    dietary_rationale: str


class ConflictMatch(BaseModel):
    rule_id: str
    matched_salt: str
    drug_class: str
    severity: Literal["HIGH", "MODERATE", "LOW"]
    conflicted_foods: list[str]
    matched_nutrients: list[str]
    interaction_type: str
    biochemical_mechanism: str
    plain_language_summary: str
    safe_time_gap_hours: dict[str, float]
    absorption_impact: dict[str, float]
    ifct_evidence: list[dict[str, Any]]
    ghar_ki_rasoi_swaps: list[GharKiRasoiSwap]
    citations: list[dict[str, str]]
    clinical_sign_off: dict[str, Any]
    recommended_earliest_meal_time: str | None = None
    absorption_curve: list[AbsorptionCurvePoint] = Field(default_factory=list)


class ConflictCheckResponse(BaseModel):
    user_id: str
    consent_id: str
    checked_salts: list[str]
    checked_foods: list[str]
    has_conflicts: bool
    highest_severity: Literal["NONE", "LOW", "MODERATE", "HIGH"]
    conflicts: list[ConflictMatch]
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER


class MedicationDoseInput(StrictNoRawImageModel):
    medicine_label: str = Field(min_length=2)
    active_salt: str = Field(min_length=2)
    preferred_time_hhmm: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class MealSlotInput(StrictNoRawImageModel):
    meal_slot: MealSlotName
    time_hhmm: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    food_items: list[str] = Field(min_length=1)
    nutrient_flags: list[str] = Field(default_factory=list)


class TimetableRequest(StrictNoRawImageModel):
    user_id: str = Field(min_length=4)
    consent_id: str = Field(min_length=4)
    medications: list[MedicationDoseInput] = Field(min_length=1)
    meals: list[MealSlotInput] = Field(min_length=1)


class TimetableEntry(BaseModel):
    entry_type: Literal["medication", "meal"]
    label: str
    original_time_hhmm: str
    recommended_time_hhmm: str
    adjusted_minutes: int
    status: Literal["safe_as_planned", "shifted_for_safe_gap", "take_with_meal_buffer", "consistency_advisory"]
    guidance: str
    rule_ids: list[str] = Field(default_factory=list)
    kitchen_swaps: list[str] = Field(default_factory=list)


class QrHealthPassPayload(BaseModel):
    pass_version: str = "1.0"
    schedule_id: str
    active_salts: list[str]
    safe_daily_summary: list[str]
    key_kitchen_swaps: list[str]
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER


class TimetableResponse(BaseModel):
    schedule_id: str
    user_id: str
    consent_id: str
    conflict_count: int
    detected_conflicts: list[ConflictMatch]
    timeline: list[TimetableEntry]
    qr_health_pass: QrHealthPassPayload
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER
    created_at_utc: str


class PrivacyAuditSummary(BaseModel):
    dpdp_compliant: bool
    raw_images_stored_count: Literal[0] = 0
    active_users_count: int
    active_consents_count: int
    withdrawn_consents_count: int
    stored_scans_count: int
    stored_schedules_count: int
    verified_rules_loaded: int
    anonymity_rule3_enforced: Literal[True] = True
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER


class DataErasureResponse(BaseModel):
    user_id: str
    erased: bool
    scans_deleted: int
    schedules_deleted: int
    consents_withdrawn: int
    message: str
