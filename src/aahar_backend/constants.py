"""Shared constants and safety notices for Aahar-Rx Member 4 Backend."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
VERIFIED_RULES_PATH = DATA_DIR / "verified_rules.json"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "aahar_rx_local.db"

CLINICAL_SAFETY_DISCLAIMER = (
    "Aahar-Rx provides timing and dietary guidance only. It never advises skipping, "
    "altering, or replacing prescribed medication dosages. Always follow your "
    "prescribing physician's instructions."
)

DPDP_DEFAULT_PURPOSE = (
    "Conflict evaluation and safe meal-medicine timetable generation using "
    "minimal confirmed medication salts and food names without retaining raw photos."
)

FORBIDDEN_RAW_IMAGE_FIELDS = frozenset(
    {
        "image_base64",
        "raw_image",
        "raw_image_bytes",
        "image_bytes",
        "photo_base64",
        "prescription_photo",
        "meal_photo",
    }
)
