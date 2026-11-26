"""Aahar-Rx Member 1 (AI & Smart Scan) public package exports."""

from .constants import CLINICAL_SAFETY_DISCLAIMER, SCHEMA_VERSION
from .meal_vision import (
    FoodTaxonomyIndex,
    MealConfirmationManager,
    MealConfirmationRequiredError,
    MealVisionService,
)
from .member2_handoff import (
    check_member2_rule_compatibility,
    load_member2_verified_rules,
    validate_bundle_against_schema,
)
from .ocr_engines import SmartStripOcrPipeline
from .pipeline import (
    AaharSmartScanPipeline,
    ConsentRequiredError,
    create_scan_consent,
)
from .salt_resolver import SaltResolver

__all__ = [
    "AaharSmartScanPipeline",
    "CLINICAL_SAFETY_DISCLAIMER",
    "ConsentRequiredError",
    "FoodTaxonomyIndex",
    "MealConfirmationManager",
    "MealConfirmationRequiredError",
    "MealVisionService",
    "SCHEMA_VERSION",
    "SaltResolver",
    "SmartStripOcrPipeline",
    "check_member2_rule_compatibility",
    "create_scan_consent",
    "load_member2_verified_rules",
    "validate_bundle_against_schema",
]
