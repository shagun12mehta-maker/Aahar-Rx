"""Unified Member 1 Smart Scan pipeline (pre-scan consent check, OCR, vision, confirmation, handoff)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .constants import CLINICAL_SAFETY_DISCLAIMER, DPDP_DEFAULT_PURPOSE, SCHEMA_VERSION
from .meal_vision import (
    FoodTaxonomyIndex,
    MealConfirmationManager,
    MealVisionService,
)
from .member2_handoff import validate_bundle_against_schema
from .models import (
    ConfirmedMealPayload,
    ConfirmedScanBundle,
    LanguageCode,
    ManualSearchHit,
    MealConfirmationUpdate,
    MealScanResult,
    MealSlot,
    Member2LookupKeys,
    ResolvedMedication,
    ScanConsentAttestation,
    StripScanResult,
)
from .ocr_engines import SmartStripOcrPipeline
from .salt_resolver import SaltResolver


class ConsentRequiredError(PermissionError):
    """Raised when image scanning is attempted without affirmative user consent."""


def create_scan_consent(
    consented: bool,
    purpose: str = DPDP_DEFAULT_PURPOSE,
) -> ScanConsentAttestation:
    """Create an ephemeral DPDP Act 2023 consent attestation prior to scanning."""
    if not consented:
        raise ConsentRequiredError(
            "Explicit DPDP Act 2023 user consent (consented=True) is required "
            "before decoding medicine strip or meal photos."
        )
    return ScanConsentAttestation(
        consented=True,
        purpose=purpose,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        retention_policy="ephemeral_in_memory",
        raw_images_retained=False,
    )


class AaharSmartScanPipeline:
    """Orchestrates Member 1 Smart Scan flow and validates handoff JSON for Member 2/4."""

    def __init__(
        self,
        salt_resolver: SaltResolver | None = None,
        strip_pipeline: SmartStripOcrPipeline | None = None,
        meal_vision: MealVisionService | None = None,
        meal_confirmations: MealConfirmationManager | None = None,
    ) -> None:
        self.salt_resolver = salt_resolver or SaltResolver()
        self.strip_pipeline = strip_pipeline or SmartStripOcrPipeline(salt_resolver=self.salt_resolver)
        self.taxonomy = FoodTaxonomyIndex()
        self.meal_vision = meal_vision or MealVisionService(taxonomy=self.taxonomy)
        self.meal_confirmations = meal_confirmations or MealConfirmationManager(taxonomy=self.taxonomy)

    @staticmethod
    def _require_consent(consent: ScanConsentAttestation | None) -> ScanConsentAttestation:
        if consent is None or not consent.consented:
            raise ConsentRequiredError(
                "Missing affirmative DPDP consent attestation prior to image scan."
            )
        return consent

    def scan_medicine_strip(
        self,
        image_bytes: bytes,
        consent: ScanConsentAttestation | None,
        bypass_quality_gate: bool = False,
    ) -> StripScanResult:
        """Scan a medicine strip image strictly in memory after consent verification."""
        self._require_consent(consent)
        scan_id = f"strip_{uuid.uuid4().hex[:12]}"
        return self.strip_pipeline.scan_bytes(
            image_bytes=image_bytes,
            scan_id=scan_id,
            bypass_quality_gate=bypass_quality_gate,
        )

    def search_medicine_fallback(self, query: str, limit: int = 8) -> list[ManualSearchHit]:
        """Manual brand/salt search fallback when OCR fails or needs correction."""
        return self.salt_resolver.search_brands_and_salts(query=query, limit=limit)

    def select_manual_medicine(
        self,
        brand_id_or_name: str,
        strength_text: str | None = None,
        intended_dose_time_hhmm: str | None = None,
        expiry_date: str | None = None,
        tablet_count: int | None = None,
    ) -> ResolvedMedication:
        """Build a confirmed medication directly from manual brand/salt selection."""
        return self.salt_resolver.build_manual_medication(
            brand_id_or_name=brand_id_or_name,
            strength_text=strength_text,
            intended_dose_time_hhmm=intended_dose_time_hhmm,
            expiry_date=expiry_date,
            tablet_count=tablet_count,
        )

    def scan_meal_photo(
        self,
        image_bytes: bytes,
        consent: ScanConsentAttestation | None,
        mime_type: str = "image/jpeg",
        meal_slot: MealSlot = "lunch",
        meal_hint: str | None = None,
        bypass_quality_gate: bool = False,
    ) -> MealScanResult:
        """Analyze a meal photo strictly in memory; returns unconfirmed AI suggestions."""
        self._require_consent(consent)
        result = self.meal_vision.analyze_meal_photo(
            image_bytes=image_bytes,
            mime_type=mime_type,
            meal_slot=meal_slot,
            meal_hint=meal_hint,
            bypass_quality_gate=bypass_quality_gate,
        )
        self.meal_confirmations.register_scan(result)
        return result

    def confirm_meal(
        self,
        session_id: str,
        update: MealConfirmationUpdate,
    ) -> ConfirmedMealPayload:
        """Record mandatory user confirmation/edits on AI meal detections."""
        return self.meal_confirmations.confirm_meal(session_id=session_id, update=update)

    def export_handoff_bundle(
        self,
        consent: ScanConsentAttestation | None,
        meal_session_id: str,
        medications: list[ResolvedMedication],
        preferred_language: LanguageCode = "en",
    ) -> ConfirmedScanBundle:
        """Assemble & JSON-Schema-validate the Member 1 -> Member 2/4 handoff bundle."""
        valid_consent = self._require_consent(consent)
        confirmed_meal = self.meal_confirmations.require_confirmed_meal(meal_session_id)

        salt_names = sorted({salt for med in medications for salt in med.active_salts})
        drug_classes = sorted({med.drug_class for med in medications})
        food_ids = [item.canonical_food_id for item in confirmed_meal.items]

        member2_labels: list[str] = []
        for item in confirmed_meal.items:
            if item.canonical_food_id == "chai_with_milk" and item.contains_milk is False:
                member2_labels.append("Black Tea (Tannins)")
                continue
            entry = self.taxonomy.get(item.canonical_food_id)
            if entry:
                for lbl in entry.get("member2_culprit_labels", []):
                    if lbl not in member2_labels:
                        member2_labels.append(lbl)
            if item.display_name not in member2_labels:
                member2_labels.append(item.display_name)

        bundle = ConfirmedScanBundle(
            schema_version=SCHEMA_VERSION,
            bundle_id=f"bundle_{uuid.uuid4().hex[:12]}",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            preferred_language=preferred_language,
            consent=valid_consent,
            medications=medications,
            confirmed_meal=confirmed_meal,
            safety_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            member2_lookup_keys=Member2LookupKeys(
                salt_names=salt_names,
                drug_classes=drug_classes,
                food_ids=food_ids,
                nutrient_flags=confirmed_meal.aggregated_interfering_nutrients,
                member2_food_labels=member2_labels,
            ),
        )
        errors = validate_bundle_against_schema(bundle)
        if errors:
            raise ValueError(f"Generated bundle failed schema validation: {errors}")
        return bundle
