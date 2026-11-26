"""Project-wide safety, privacy, and taxonomy constants for Aahar-Rx Smart Scan (Member 1)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "salt_food_schema.json"

SCHEMA_VERSION = "1.0.0"

CLINICAL_SAFETY_DISCLAIMER = (
    "Aahar-Rx provides timing and dietary guidance only. It never advises skipping, "
    "altering, or replacing prescribed medication dosages. Consult your doctor or "
    "pharmacist before making any change to your treatment plan."
)

DPDP_DEFAULT_PURPOSE = (
    "Ephemeral AI scanning of medication strip and meal photos to identify active "
    "salts and food nutrients for safe meal-medicine timing guidance."
)

SUPPORTED_LANGUAGES = ("en", "hi", "mr")

DRUG_CLASSES = (
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
)

MEAL_SLOTS = (
    "early_morning_empty_stomach",
    "breakfast",
    "mid_morning",
    "lunch",
    "evening_chai_snack",
    "dinner",
    "bedtime",
)

TRACKED_INTERFERENTS = (
    "calcium",
    "iron",
    "oxalates",
    "tannins_polyphenols",
    "vitamin_k",
    "caffeine",
    "high_fat",
    "high_fiber",
    "phytates",
    "potassium",
    "tyramine",
    "grapefruit_furanocoumarins",
    "simple_sugars",
    "soy_isoflavones",
)
