"""Day 7 Live Demo Rehearsal Runner for Aahar-Rx Smart Scan (Member 1)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from aahar_scan.constants import DATA_DIR  # noqa: E402
from aahar_scan.meal_vision import MealVisionService  # noqa: E402
from aahar_scan.member2_handoff import (  # noqa: E402
    check_member2_rule_compatibility,
    load_member2_verified_rules,
)
from aahar_scan.models import MealConfirmationUpdate  # noqa: E402
from aahar_scan.pipeline import AaharSmartScanPipeline, create_scan_consent  # noqa: E402
from fixtures.generate_test_assets import generate_meal_image_bytes, generate_strip_image_bytes  # noqa: E402


def main() -> None:
    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    rules = load_member2_verified_rules(DATA_DIR / "verified_rules.json")

    print("=== [1/5] DPDP Act 2023 Ephemeral Pre-Scan Consent ===")
    consent = create_scan_consent(True)
    print("Consent granted:", consent.consented, "| Raw images retained:", consent.raw_images_retained)

    print("\n=== [2/5] Stage Lighting Failure & Retry Guidance ===")
    blur_res = pipeline.scan_medicine_strip(generate_strip_image_bytes("15_fail_severe_blur"), consent)
    print("Retry required:", blur_res.retry_required, "| Guidance:", blur_res.quality_report.retry_guidance)

    print("\n=== [3/5] Glare Foil Recovery & Salt Resolution ===")
    glare_res = pipeline.scan_medicine_strip(generate_strip_image_bytes("03_shelcal_glare"), consent)
    top_med = glare_res.resolved_medications[0]
    print("Resolved:", top_med.brand_name, "->", top_med.active_salts, "| Class:", top_med.drug_class)

    print("\n=== [4/5] Manual Brand/Salt Fallback Search ===")
    hits = pipeline.search_medicine_fallback("thyronorm", limit=2)
    print("Top fallback search hit:", hits[0].brand_name, "->", hits[0].active_salts)
    thyroid_med = pipeline.select_manual_medicine("thyronorm", intended_dose_time_hhmm="07:00")

    print("\n=== [5/5] Meal Vision + Mandatory Confirmation + Member 2 Compatibility ===")
    meal_scan = pipeline.scan_meal_photo(
        generate_meal_image_bytes("morning_chai_with_milk"),
        consent,
        meal_slot="early_morning_empty_stomach",
        meal_hint="masala chai with milk",
    )
    print("Initial confirmation status:", meal_scan.confirmation_status)
    confirmed_meal = pipeline.confirm_meal(
        meal_scan.session_id,
        MealConfirmationUpdate(confirm_food_ids=["chai_with_milk"], scheduled_time_hhmm="07:20"),
    )
    print("Confirmed status:", confirmed_meal.confirmation_status, "| Nutrients:", confirmed_meal.aggregated_interfering_nutrients)

    bundle = pipeline.export_handoff_bundle(
        consent=consent,
        meal_session_id=meal_scan.session_id,
        medications=[thyroid_med, top_med],
        preferred_language="hi",
    )
    matched = check_member2_rule_compatibility(bundle, rules)
    print("\nValidated Bundle ID:", bundle.bundle_id)
    print("Compatible Member 2 Rule IDs:", json.dumps(matched))


if __name__ == "__main__":
    main()
