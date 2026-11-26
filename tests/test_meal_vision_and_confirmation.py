"""Tests for Gemini 2.5 Flash Meal Vision JSON parsing, offline fallback, and mandatory confirmation."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aahar_scan.meal_vision import (
    MealConfirmationRequiredError,
    MealVisionService,
)
from aahar_scan.models import MealConfirmationUpdate
from aahar_scan.pipeline import AaharSmartScanPipeline, create_scan_consent
from fixtures.generate_test_assets import generate_meal_image_bytes, generate_strip_image_bytes


class _FakeGeminiModels:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(text=json.dumps(self.payload))


class _FakeGeminiClient:
    def __init__(self, payload: dict) -> None:
        self.models = _FakeGeminiModels(payload)


def test_gemini_25_flash_vision_multimodal_json_grounding() -> None:
    fake_payload = {
        "meal_slot_guess": "breakfast",
        "detected_items": [
            {
                "dish_name": "Masala Chai with Milk",
                "contains_milk": True,
                "portion_hint": "1 cup (150 ml)",
                "interfering_nutrients": ["tannins_polyphenols", "calcium"],
                "confidence": 0.94,
            },
            {
                "dish_name": "Palak Paneer",
                "canonical_food_id": "palak_spinach",
                "portion_hint": "1 katori",
                "confidence": 0.89,
            },
            {
                "dish_name": "Homemade Besan Chilla",
                "portion_hint": "2 pieces",
                "interfering_nutrients": ["high_fiber"],
                "confidence": 0.71,
            },
        ],
    }
    fake_client = _FakeGeminiClient(fake_payload)
    vision = MealVisionService(genai_client=fake_client)
    img_bytes = generate_meal_image_bytes("morning_chai_with_milk")

    res = vision.analyze_meal_photo(
        img_bytes, mime_type="image/png", meal_slot="breakfast", meal_hint="chai"
    )
    assert res.vision_provider == "gemini-2.5-flash"
    assert res.confirmation_status == "pending_user_confirmation"
    assert res.requires_user_confirmation is True
    assert len(fake_client.models.calls) == 1
    call = fake_client.models.calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert call["config"].response_mime_type == "application/json"

    ids = [item.canonical_food_id for item in res.suggested_items]
    assert "chai_with_milk" in ids
    assert "palak_spinach" in ids
    chilla = [i for i in res.suggested_items if i.canonical_food_id == "homemade_besan_chilla"][0]
    assert chilla.low_confidence_flag is True


def test_offline_meal_plate_analyzer_and_retry_flow() -> None:
    vision = MealVisionService(api_key="")
    thali_res = vision.analyze_meal_photo(
        generate_meal_image_bytes("thali_palak_dal_curd"),
        meal_slot="lunch",
    )
    assert thali_res.retry_required is False
    ids = {i.canonical_food_id for i in thali_res.suggested_items}
    assert "palak_spinach" in ids
    assert "dal_lentils" in ids

    blur_res = vision.analyze_meal_photo(generate_meal_image_bytes("meal_severe_blur"), meal_slot="lunch")
    assert blur_res.retry_required is True
    assert blur_res.suggested_items == []


def test_mandatory_confirmation_blocks_unconfirmed_export_and_applies_edits() -> None:
    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    consent = create_scan_consent(True)
    strip_res = pipeline.scan_medicine_strip(generate_strip_image_bytes("01_thyronorm_clean"), consent)
    meal_res = pipeline.scan_meal_photo(
        generate_meal_image_bytes("morning_chai_with_milk"),
        consent,
        meal_slot="early_morning_empty_stomach",
        meal_hint="masala chai with milk",
    )

    with pytest.raises(MealConfirmationRequiredError):
        pipeline.export_handoff_bundle(
            consent=consent,
            meal_session_id=meal_res.session_id,
            medications=strip_res.resolved_medications,
        )

    confirmed = pipeline.confirm_meal(
        session_id=meal_res.session_id,
        update=MealConfirmationUpdate(
            confirm_food_ids=["chai_with_milk"],
            add_food_ids=["citrus_amla_lemon"],
            milk_overrides={"chai_with_milk": False},
            portion_overrides={"chai_with_milk": "1 small cup"},
            scheduled_time_hhmm="07:30",
        ),
    )
    assert confirmed.confirmed_by_user is True
    assert confirmed.confirmation_status == "modified_by_user"
    chai = [i for i in confirmed.items if i.canonical_food_id == "chai_with_milk"][0]
    assert chai.contains_milk is False
    assert "calcium" not in chai.interfering_nutrients
    assert "tannins_polyphenols" in chai.interfering_nutrients
    assert chai.source == "vision_edited"

    bundle = pipeline.export_handoff_bundle(
        consent=consent,
        meal_session_id=meal_res.session_id,
        medications=strip_res.resolved_medications,
    )
    assert bundle.confirmed_meal.confirmed_by_user is True
    assert "tannins_polyphenols" in bundle.member2_lookup_keys.nutrient_flags
