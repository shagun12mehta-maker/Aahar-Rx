"""Gemini 2.5 Flash Meal & Salt Vision module with mandatory user confirmation."""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re
from typing import Any
import uuid

import cv2
import numpy as np
from rapidfuzz import fuzz

from .constants import DATA_DIR, TRACKED_INTERFERENTS
from .models import (
    ConfirmedFoodItem,
    ConfirmedMealPayload,
    MealConfirmationUpdate,
    MealItemSuggestion,
    MealScanResult,
    MealSlot,
)
from .preprocessing import decode_image_bytes, inspect_image_quality


class MealConfirmationRequiredError(RuntimeError):
    """Raised when attempting to export unconfirmed AI meal suggestions."""


_GEMINI_MEAL_RESPONSE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["detected_items"],
    "properties": {
        "meal_slot_guess": {"type": "string"},
        "detected_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["dish_name", "confidence"],
                "properties": {
                    "dish_name": {"type": "string"},
                    "canonical_food_id": {"type": "string"},
                    "contains_milk": {"type": "boolean"},
                    "portion_hint": {"type": "string"},
                    "interfering_nutrients": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confidence": {"type": "number"},
                },
            },
        },
    },
}

_GEMINI_SYSTEM_PROMPT = (
    "You are Aahar-Rx Meal & Salt Vision AI analyzing Indian home and restaurant meals "
    "(Thali, chai, milk, curd/dahi, paneer, palak/saag, dal, roti, rice, citrus, fried items). "
    "Return ONLY valid JSON matching the schema. Flag whether tea/coffee includes milk, "
    "distinguish leafy greens like palak/methi, and list interacting nutrients from: "
    + ", ".join(TRACKED_INTERFERENTS)
    + ". Never invent medical dosages or advise changing prescriptions."
)


@lru_cache(maxsize=4)
def load_food_taxonomy(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the ICMR-NIN IFCT aligned Indian food taxonomy from disk."""
    target = path or (DATA_DIR / "indian_food_taxonomy.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload["foods"]


class FoodTaxonomyIndex:
    """Lookup & normalization index for Indian foods and nutrient interferents."""

    def __init__(self, taxonomy_path: Path | None = None) -> None:
        self.foods = load_food_taxonomy(taxonomy_path)
        self._by_id = {item["canonical_food_id"]: item for item in self.foods}

    def get(self, food_id: str) -> dict[str, Any] | None:
        return self._by_id.get(food_id)

    def match_dish_name(self, dish_name: str, canonical_hint: str | None = None) -> dict[str, Any] | None:
        """Resolve a free-form dish label from Vision AI onto a canonical taxonomy entry."""
        if canonical_hint and canonical_hint in self._by_id:
            return self._by_id[canonical_hint]

        q = re.sub(r"[^a-z0-9\s]", " ", dish_name.lower()).strip()
        if not q:
            return None

        best_score = 0.0
        best_entry: dict[str, Any] | None = None
        for entry in self.foods:
            terms = [entry["canonical_food_id"].replace("_", " "), entry["display_name"].lower(), *entry.get("keywords", [])]
            for term in terms:
                norm_term = re.sub(r"[^a-z0-9\s]", " ", term.lower()).strip()
                if not norm_term:
                    continue
                if norm_term == q:
                    return entry
                if re.search(rf"\b{re.escape(norm_term)}\b", q) or re.search(rf"\b{re.escape(q)}\b", norm_term):
                    score = (0.96 if len(norm_term) >= 4 else 0.85) + min(0.039, len(norm_term) / 1000.0)
                else:
                    score = fuzz.ratio(q, norm_term) / 100.0
                if score > best_score:
                    best_score = score
                    best_entry = entry
        return best_entry if best_score >= 0.78 else None

    def search_foods(self, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        """Search Indian foods for user addition during mandatory confirmation."""
        q = query.strip().lower()
        if not q:
            return self.foods[:limit]
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self.foods:
            hay = " ".join([entry["display_name"], *entry.get("keywords", [])]).lower()
            if q in hay:
                score = 0.98
            else:
                score = fuzz.partial_ratio(q, hay) / 100.0
            if score >= 0.50:
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]


class MealVisionService:
    """Detects Indian meal components using Gemini 2.5 Flash Vision (with offline fallback)."""

    def __init__(
        self,
        taxonomy: FoodTaxonomyIndex | None = None,
        api_key: str | None = None,
        genai_client: Any | None = None,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self.taxonomy = taxonomy or FoodTaxonomyIndex()
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self._injected_client = genai_client
        self.model_name = model_name

    def _get_genai_client(self):
        if self._injected_client is not None:
            return self._injected_client
        if not self.api_key:
            return None
        from google import genai

        return genai.Client(api_key=self.api_key)

    def _build_suggestion(
        self,
        entry: dict[str, Any],
        confidence: float,
        portion_hint: str | None = None,
        contains_milk: bool | None = None,
        extra_nutrients: list[str] | None = None,
    ) -> MealItemSuggestion:
        nutrients = list(entry.get("interfering_nutrients", []))
        if extra_nutrients:
            for nut in extra_nutrients:
                if nut in TRACKED_INTERFERENTS and nut not in nutrients:
                    nutrients.append(nut)

        effective_milk = entry.get("contains_milk") if contains_milk is None else contains_milk
        if effective_milk is False and "calcium" in nutrients and entry["category"] == "beverage_tea_coffee":
            nutrients = [n for n in nutrients if n != "calcium"]
        elif effective_milk is True and "calcium" not in nutrients and entry["category"] == "beverage_tea_coffee":
            nutrients.append("calcium")

        return MealItemSuggestion(
            canonical_food_id=entry["canonical_food_id"],
            display_name=entry["display_name"],
            hindi_name=entry.get("hindi_name"),
            marathi_name=entry.get("marathi_name"),
            category=entry["category"],
            interfering_nutrients=nutrients,
            portion_hint=portion_hint or "1 standard serving",
            contains_milk=effective_milk,
            confidence=round(max(0.0, min(1.0, confidence)), 3),
            confirmation_question=entry.get("confirmation_question"),
            low_confidence_flag=confidence < 0.78,
        )

    def _parse_gemini_json(self, raw_json_text: str) -> list[MealItemSuggestion]:
        payload = json.loads(raw_json_text)
        raw_items = payload.get("detected_items", [])
        suggestions: list[MealItemSuggestion] = []
        seen_ids: set[str] = set()

        for item in raw_items:
            dish_name = str(item.get("dish_name", "")).strip()
            canonical_hint = item.get("canonical_food_id")
            entry = self.taxonomy.match_dish_name(dish_name, canonical_hint=canonical_hint)
            if entry is None:
                fid = re.sub(r"[^a-z0-9]+", "_", dish_name.lower()).strip("_") or "custom_dish"
                if fid in seen_ids:
                    continue
                seen_ids.add(fid)
                nutrients = [
                    n for n in item.get("interfering_nutrients", []) if n in TRACKED_INTERFERENTS
                ]
                conf = float(item.get("confidence", 0.6))
                suggestions.append(
                    MealItemSuggestion(
                        canonical_food_id=fid,
                        display_name=dish_name or "Detected Meal Item",
                        category="other",
                        interfering_nutrients=nutrients,
                        portion_hint=item.get("portion_hint") or "1 serving",
                        contains_milk=item.get("contains_milk"),
                        confidence=round(conf, 3),
                        confirmation_question=f"Confirm '{dish_name}' and its dairy/leafy ingredients.",
                        low_confidence_flag=conf < 0.78,
                    )
                )
                continue

            fid = entry["canonical_food_id"]
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            suggestions.append(
                self._build_suggestion(
                    entry=entry,
                    confidence=float(item.get("confidence", 0.85)),
                    portion_hint=item.get("portion_hint"),
                    contains_milk=item.get("contains_milk"),
                    extra_nutrients=item.get("interfering_nutrients"),
                )
            )
        return suggestions

    def _call_gemini_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        meal_slot: MealSlot,
        meal_hint: str | None = None,
    ) -> list[MealItemSuggestion]:
        from google.genai import types

        client = self._get_genai_client()
        if client is None:
            raise RuntimeError("Gemini API key or client not configured.")

        user_prompt = (
            f"Analyze this Indian meal photo for the '{meal_slot}' slot. "
            "List every visible dish, beverage, dairy item (milk/curd/paneer/chaas/chai with milk), "
            "or leafy green (palak/methi/saag)."
        )
        if meal_hint:
            user_prompt += f" User note: {meal_hint}"

        response = client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                user_prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=_GEMINI_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
                response_json_schema=_GEMINI_MEAL_RESPONSE_JSON_SCHEMA,
            ),
        )
        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise RuntimeError("Empty response from Gemini Vision API.")
        return self._parse_gemini_json(raw_text)

    def _analyze_offline_plate(
        self,
        bgr: np.ndarray,
        meal_slot: MealSlot,
        meal_hint: str | None = None,
    ) -> list[MealItemSuggestion]:
        """Offline HSV color-region & hint heuristic when GEMINI_API_KEY is absent."""
        suggestions: list[MealItemSuggestion] = []
        seen: set[str] = set()

        def _add(food_id: str, conf: float, portion: str | None = None) -> None:
            if food_id in seen:
                return
            entry = self.taxonomy.get(food_id)
            if entry:
                seen.add(food_id)
                suggestions.append(self._build_suggestion(entry, conf, portion_hint=portion))

        if meal_hint:
            hint_lower = meal_hint.lower()
            for entry in self.taxonomy.foods:
                if any(kw in hint_lower for kw in entry.get("keywords", [])):
                    _add(entry["canonical_food_id"], 0.84)

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        green_leafy_ratio = float(np.mean((h >= 34) & (h <= 85) & (s >= 55) & (v >= 35) & (v <= 210)))
        turmeric_dal_ratio = float(np.mean((h >= 16) & (h <= 33) & (s >= 90) & (v >= 120)))
        chai_brown_ratio = float(np.mean((h >= 8) & (h <= 22) & (s >= 45) & (s <= 170) & (v >= 70) & (v <= 195)))
        creamy_white_ratio = float(np.mean((s <= 32) & (v >= 195) & (v <= 248)))

        if green_leafy_ratio > 0.03:
            _add("palak_spinach", min(0.76, 0.58 + green_leafy_ratio), "1 katori")
        if turmeric_dal_ratio > 0.03:
            _add("dal_lentils", min(0.76, 0.60 + turmeric_dal_ratio), "1 katori")
        if chai_brown_ratio > 0.14 and meal_slot in ("early_morning_empty_stomach", "breakfast", "evening_chai_snack"):
            _add("chai_with_milk", 0.72, "1 cup")
        if creamy_white_ratio > 0.14:
            if meal_slot in ("lunch", "dinner"):
                _add("curd_dahi", 0.68, "1 small katori")
            elif "chai_with_milk" not in seen:
                _add("cow_milk", 0.67, "1 glass")

        if not suggestions:
            if meal_slot in ("early_morning_empty_stomach", "evening_chai_snack"):
                _add("chai_with_milk", 0.58, "1 cup")
            elif meal_slot == "breakfast":
                _add("poha_upma", 0.58, "1 plate")
                _add("chai_with_milk", 0.56, "1 cup")
            else:
                _add("dal_lentils", 0.58, "1 katori")
                _add("wheat_roti", 0.56, "2 rotis")

        return suggestions

    def analyze_meal_photo(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        meal_slot: MealSlot = "lunch",
        meal_hint: str | None = None,
        bypass_quality_gate: bool = False,
    ) -> MealScanResult:
        """Inspect meal photo quality and extract candidate dishes awaiting user confirmation."""
        bgr = decode_image_bytes(image_bytes)
        quality = inspect_image_quality(bgr, mode="meal")
        session_id = f"meal_{uuid.uuid4().hex[:12]}"

        quick_adds = [
            "chai_with_milk",
            "cow_milk",
            "curd_dahi",
            "palak_spinach",
            "dal_lentils",
            "wheat_roti",
            "steamed_rice",
        ]

        if not quality.passed and not bypass_quality_gate:
            return MealScanResult(
                session_id=session_id,
                quality_report=quality,
                retry_required=True,
                vision_provider="quality_gate_rejected",
                meal_slot=meal_slot,
                suggested_items=[],
                quick_add_candidates=quick_adds,
            )

        provider = "offline_plate_heuristic"
        suggestions: list[MealItemSuggestion]
        client = self._get_genai_client()
        if client is not None:
            try:
                suggestions = self._call_gemini_vision(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    meal_slot=meal_slot,
                    meal_hint=meal_hint,
                )
                provider = self.model_name
            except Exception:
                suggestions = self._analyze_offline_plate(bgr, meal_slot=meal_slot, meal_hint=meal_hint)
                provider = "offline_plate_heuristic_fallback"
        else:
            suggestions = self._analyze_offline_plate(bgr, meal_slot=meal_slot, meal_hint=meal_hint)

        return MealScanResult(
            session_id=session_id,
            quality_report=quality,
            retry_required=False,
            vision_provider=provider,
            meal_slot=meal_slot,
            suggested_items=suggestions,
            quick_add_candidates=quick_adds,
        )


class MealConfirmationManager:
    """Enforces mandatory human-in-the-loop confirmation after meal-photo detection."""

    def __init__(self, taxonomy: FoodTaxonomyIndex | None = None) -> None:
        self.taxonomy = taxonomy or FoodTaxonomyIndex()
        self._pending: dict[str, MealScanResult] = {}
        self._confirmed: dict[str, ConfirmedMealPayload] = {}

    def register_scan(self, scan: MealScanResult) -> None:
        """Register an AI meal scan in pending confirmation state."""
        self._pending[scan.session_id] = scan

    def get_pending(self, session_id: str) -> MealScanResult:
        if session_id not in self._pending:
            raise KeyError(f"Unknown meal session_id: {session_id}")
        return self._pending[session_id]

    def confirm_meal(
        self,
        session_id: str,
        update: MealConfirmationUpdate,
    ) -> ConfirmedMealPayload:
        """Apply user edits/confirmations and freeze the meal payload for clinical rules."""
        pending = self.get_pending(session_id)
        if pending.retry_required and not update.add_food_ids:
            raise ValueError(
                "Meal photo failed quality check; retake the photo or manually add foods."
            )

        removed = set(update.remove_food_ids)
        explicit_keep = set(update.confirm_food_ids)
        modified = bool(
            removed
            or update.add_food_ids
            or update.milk_overrides
            or update.portion_overrides
            or (update.meal_slot and update.meal_slot != pending.meal_slot)
        )

        final_items: list[ConfirmedFoodItem] = []
        seen_ids: set[str] = set()

        for suggestion in pending.suggested_items:
            fid = suggestion.canonical_food_id
            if fid in removed:
                continue
            if explicit_keep and fid not in explicit_keep:
                modified = True
                continue

            nutrients = list(suggestion.interfering_nutrients)
            contains_milk = suggestion.contains_milk
            item_edited = False

            if fid in update.milk_overrides:
                contains_milk = update.milk_overrides[fid]
                item_edited = True
                if contains_milk and "calcium" not in nutrients:
                    nutrients.append("calcium")
                elif not contains_milk and "calcium" in nutrients and suggestion.category == "beverage_tea_coffee":
                    nutrients = [n for n in nutrients if n != "calcium"]

            portion = update.portion_overrides.get(fid, suggestion.portion_hint)
            if fid in update.portion_overrides:
                item_edited = True

            seen_ids.add(fid)
            final_items.append(
                ConfirmedFoodItem(
                    canonical_food_id=fid,
                    display_name=suggestion.display_name,
                    hindi_name=suggestion.hindi_name,
                    marathi_name=suggestion.marathi_name,
                    category=suggestion.category,
                    interfering_nutrients=sorted(set(nutrients)),
                    portion_hint=portion,
                    contains_milk=contains_milk,
                    source="vision_edited" if item_edited else "vision_confirmed",
                    confidence=suggestion.confidence,
                )
            )

        for add_id in update.add_food_ids:
            if add_id in seen_ids:
                continue
            entry = self.taxonomy.get(add_id)
            if entry is None:
                raise KeyError(f"Unknown canonical_food_id in add_food_ids: {add_id}")
            nutrients = list(entry.get("interfering_nutrients", []))
            contains_milk = entry.get("contains_milk")
            if add_id in update.milk_overrides:
                contains_milk = update.milk_overrides[add_id]
                if contains_milk and "calcium" not in nutrients:
                    nutrients.append("calcium")
                elif not contains_milk and "calcium" in nutrients and entry["category"] == "beverage_tea_coffee":
                    nutrients = [n for n in nutrients if n != "calcium"]

            seen_ids.add(add_id)
            final_items.append(
                ConfirmedFoodItem(
                    canonical_food_id=add_id,
                    display_name=entry["display_name"],
                    hindi_name=entry.get("hindi_name"),
                    marathi_name=entry.get("marathi_name"),
                    category=entry["category"],
                    interfering_nutrients=sorted(set(nutrients)),
                    portion_hint=update.portion_overrides.get(add_id, "1 standard serving"),
                    contains_milk=contains_milk,
                    source="user_added",
                    confidence=1.0,
                )
            )

        if not final_items:
            raise ValueError("Cannot confirm an empty meal; keep or add at least one food item.")

        aggregated = sorted(
            {nut for item in final_items for nut in item.interfering_nutrients}
        )
        payload = ConfirmedMealPayload(
            session_id=session_id,
            confirmation_status="modified_by_user" if modified else "confirmed",
            confirmed_by_user=True,
            meal_slot=update.meal_slot or pending.meal_slot,
            scheduled_time_hhmm=update.scheduled_time_hhmm,
            items=final_items,
            aggregated_interfering_nutrients=aggregated,
        )
        self._confirmed[session_id] = payload
        return payload

    def require_confirmed_meal(self, session_id: str) -> ConfirmedMealPayload:
        """Block downstream export unless the user explicitly confirmed the meal."""
        if session_id not in self._confirmed:
            raise MealConfirmationRequiredError(
                "AI meal guesses are never treated as final. User confirmation is mandatory "
                f"before exporting meal session '{session_id}'."
            )
        return self._confirmed[session_id]
