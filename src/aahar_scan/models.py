"""Pydantic data contracts for Member 1 (AI & Smart Scan) and Member 2/4 handoff."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator

from .constants import CLINICAL_SAFETY_DISCLAIMER, DPDP_DEFAULT_PURPOSE, SCHEMA_VERSION

LanguageCode = Literal["en", "hi", "mr"]
MealSlot = Literal[
    "early_morning_empty_stomach",
    "breakfast",
    "mid_morning",
    "lunch",
    "evening_chai_snack",
    "dinner",
    "bedtime",
]
DrugClass = Literal[
    "thyroid",
    "diabetes",
    "blood_pressure",
    "anaemia_supplement",
    "antibiotic",
    "anticoagulant",
    "statin",
    "gastric_ppi",
    "diuretic",
    "bone_health",
    "analgesic_nsaid",
    "other",
]


class ScanConsentAttestation(BaseModel):
    """Ephemeral DPDP Act 2023 consent attestation passed before decoding any photo."""

    consented: Literal[True] = True
    purpose: str = Field(default=DPDP_DEFAULT_PURPOSE, min_length=5)
    timestamp_utc: str
    retention_policy: Literal["ephemeral_in_memory", "session_only_no_raw_image"] = (
        "ephemeral_in_memory"
    )
    raw_images_retained: Literal[False] = False


class ImageQualityReport(BaseModel):
    """OpenCV image quality diagnostics and actionable retry guidance."""

    passed: bool
    quality_score: float = Field(ge=0.0, le=1.0)
    blur_score: float = Field(ge=0.0)
    glare_ratio: float = Field(ge=0.0, le=1.0)
    mean_brightness: float = Field(ge=0.0, le=255.0)
    contrast_std: float = Field(ge=0.0)
    estimated_skew_deg: float = 0.0
    issues: list[str] = Field(default_factory=list)
    retry_guidance: list[str] = Field(default_factory=list)
    preprocessing_applied: list[str] = Field(default_factory=list)


class OcrEngineAttempt(BaseModel):
    """Telemetry from running one OCR backend on one image variant."""

    engine_name: str
    variant_name: str
    raw_text: str
    lines: list[str] = Field(default_factory=list)
    mean_confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)


class ResolvedMedication(BaseModel):
    """Brand-to-salt resolution result ready for confirmation and conflict check."""

    brand_name: str = Field(min_length=1)
    active_salts: list[str] = Field(min_length=1)
    strength_text: str | None = None
    drug_class: DrugClass
    resolution_source: Literal["ocr_exact", "ocr_fuzzy", "salt_direct", "manual_fallback"]
    ocr_engine_used: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    confirmed_by_user: bool = False
    intended_dose_time_hhmm: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    expiry_date: str | None = Field(
        default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"
    )
    expiry_raw_text: str | None = None
    tablet_count: int | None = Field(default=None, ge=1, le=1000)
    medicine_box_fallback_needed: bool = False


class ManualSearchHit(BaseModel):
    """Candidate returned by the manual brand/salt search fallback."""

    brand_id: str
    brand_name: str
    active_salts: list[str]
    drug_class: DrugClass
    common_strengths: list[str] = Field(default_factory=list)
    is_regional_brand: bool = False
    score: float = Field(ge=0.0, le=1.0)


class StripScanResult(BaseModel):
    """Complete medicine strip Smart Scan output including retry/fallback hints."""

    scan_id: str
    quality_report: ImageQualityReport
    retry_required: bool
    ocr_engine_used: str | None = None
    raw_text: str = ""
    attempts: list[OcrEngineAttempt] = Field(default_factory=list)
    resolved_medications: list[ResolvedMedication] = Field(default_factory=list)
    needs_manual_fallback: bool = False
    manual_suggestions: list[ManualSearchHit] = Field(default_factory=list)
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER


class MealItemSuggestion(BaseModel):
    """Single AI-detected food item awaiting mandatory user confirmation."""

    canonical_food_id: str = Field(min_length=2)
    display_name: str = Field(min_length=1)
    hindi_name: str | None = None
    marathi_name: str | None = None
    category: Literal[
        "dairy",
        "beverage_tea_coffee",
        "leafy_vegetable",
        "legume_dal",
        "grain_cereal",
        "citrus_fruit",
        "fermented_food",
        "high_fat_fried",
        "supplement_fortified",
        "other",
    ]
    interfering_nutrients: list[str] = Field(default_factory=list)
    portion_hint: str | None = None
    contains_milk: bool | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    confirmation_question: str | None = None
    low_confidence_flag: bool = False


class MealScanResult(BaseModel):
    """Output of Meal & Salt Vision BEFORE mandatory user confirmation."""

    session_id: str
    quality_report: ImageQualityReport
    retry_required: bool
    vision_provider: str
    meal_slot: MealSlot = "lunch"
    confirmation_status: Literal["pending_user_confirmation"] = "pending_user_confirmation"
    requires_user_confirmation: Literal[True] = True
    suggested_items: list[MealItemSuggestion] = Field(default_factory=list)
    quick_add_candidates: list[str] = Field(default_factory=list)
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER


class ConfirmedFoodItem(BaseModel):
    """User-confirmed (or user-edited/added) food item ready for clinical rule checks."""

    canonical_food_id: str = Field(min_length=2)
    display_name: str = Field(min_length=1)
    hindi_name: str | None = None
    marathi_name: str | None = None
    category: Literal[
        "dairy",
        "beverage_tea_coffee",
        "leafy_vegetable",
        "legume_dal",
        "grain_cereal",
        "citrus_fruit",
        "fermented_food",
        "high_fat_fried",
        "supplement_fortified",
        "other",
    ]
    interfering_nutrients: list[str] = Field(default_factory=list)
    portion_hint: str | None = None
    contains_milk: bool | None = None
    source: Literal["vision_confirmed", "vision_edited", "user_added"]
    confidence: float = Field(ge=0.0, le=1.0)


class MealConfirmationUpdate(BaseModel):
    """User review payload confirming, editing, adding, or removing AI meal guesses."""

    confirm_food_ids: list[str] = Field(default_factory=list)
    add_food_ids: list[str] = Field(default_factory=list)
    remove_food_ids: list[str] = Field(default_factory=list)
    milk_overrides: dict[str, bool] = Field(default_factory=dict)
    portion_overrides: dict[str, str] = Field(default_factory=dict)
    meal_slot: MealSlot | None = None
    scheduled_time_hhmm: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )


class ConfirmedMealPayload(BaseModel):
    """Finalized user-confirmed meal state; never emitted directly from raw AI guesses."""

    session_id: str
    confirmation_status: Literal["confirmed", "modified_by_user"]
    confirmed_by_user: Literal[True] = True
    meal_slot: MealSlot
    scheduled_time_hhmm: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    items: list[ConfirmedFoodItem] = Field(min_length=1)
    aggregated_interfering_nutrients: list[str] = Field(default_factory=list)


class Member2LookupKeys(BaseModel):
    """Normalized lookup keys consumed directly by Member 2/4 conflict engine."""

    salt_names: list[str]
    drug_classes: list[str]
    food_ids: list[str]
    nutrient_flags: list[str]
    member2_food_labels: list[str] = Field(default_factory=list)


class ConfirmedScanBundle(BaseModel):
    """Top-level Member 1 -> Member 2/4 integration bundle validated against JSON Schema."""

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    bundle_id: str = Field(min_length=4)
    created_at_utc: str
    preferred_language: LanguageCode = "en"
    consent: ScanConsentAttestation
    medications: list[ResolvedMedication] = Field(min_length=1)
    confirmed_meal: ConfirmedMealPayload
    safety_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER
    member2_lookup_keys: Member2LookupKeys

    @field_validator("medications")
    @classmethod
    def _ensure_at_least_one_salt(
        cls, meds: list[ResolvedMedication]
    ) -> list[ResolvedMedication]:
        if not meds:
            raise ValueError("At least one resolved medication is required.")
        return meds
