"""Deterministic clinical conflict-detection engine & pharmacokinetic curve generator."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

from .models import (
    AbsorptionCurvePoint,
    ConflictMatch,
    GharKiRasoiSwap,
)

# Maps normalized food IDs / nutrient flags from Member 1 onto Member 2 rule terms
_FOOD_ID_TO_ALIASES: dict[str, list[str]] = {
    "chai_with_milk": ["Morning Masala Chai with Milk", "Masala Chai", "Sweetened Chai / Sherbet"],
    "black_tea": ["Masala Chai"],
    "coffee_with_milk": ["Filter Coffee"],
    "cow_milk": ["Cow/Buffalo Milk", "Doodh (Milk)"],
    "curd_dahi": ["Dahi / Curd", "Dahi (Curd)"],
    "buttermilk_chaas": ["Chaas / Buttermilk"],
    "paneer_dish": ["Paneer", "Palak Paneer"],
    "palak_spinach": ["Palak Paneer"],
    "sarson_ka_saag": ["Sarson ka Saag"],
    "methi_fenugreek": ["Methi Thepla / Methi Bhaji"],
    "green_chutney_coriander_mint": ["Green Coriander & Mint Chutney"],
    "soya_vadi_chunks": ["Soya Vadi / Soya Chunks"],
    "walnuts": ["Walnuts"],
    "rajma_chole": ["Whole pulses (Rajma/Chana)"],
    "wheat_roti": ["Bran-rich Atta Roti"],
    "maida_naan_bhatura": ["Maida Naan / Bhatura"],
    "samosa_fried": ["Deep-fried pakoras / Poori (High Re-heated Vanaspati)"],
    "gulab_jamun_sweets": ["Gulab Jamun / Jalebi"],
    "banana": ["Bananas"],
    "jackfruit_kathal": ["Jackfruit / Kathal"],
    "tender_coconut_water": ["Tender Coconut Water (multiple glasses)"],
    "sendha_namak_rock_salt": ["Sendha Namak (Rock Salt / Low Sodium Salt)"],
    "mosambi_sweet_lime_juice": ["Mosambi (Sweet Lime) Juice in large volume"],
    "grapefruit_chakotra": ["Chakotra (Grapefruit / Pomelo)", "Pomelo / Concentrated Citrus Juice"],
}

_NUTRIENT_SYNONYMS: dict[str, set[str]] = {
    "calcium": {"calcium", "calcium & magnesium"},
    "tannins_polyphenols": {"tannins", "polyphenols", "tannins / polyphenols", "total polyphenols / tannins"},
    "phytates": {"phytates", "phytic acid"},
    "oxalates": {"oxalates", "total oxalates"},
    "vitamin_k": {"phylloquinone (vitamin k1)", "vitamin k", "vitamin k1"},
    "grapefruit_furanocoumarins": {"furanocoumarins", "flavonoids (naringin)"},
    "potassium": {"potassium (k+)", "potassium"},
    "simple_sugars": {"simple sugars / high glycemic load", "simple sugars"},
    "high_fat": {"saturated fats", "saturated trans fats"},
    "soy_isoflavones": {"soy isoflavones"},
}


def build_pharmacokinetic_curve(
    bioavailability_drop_pct: float,
    t_max_delay_hours: float,
    base_tmax_hours: float = 1.5,
) -> list[AbsorptionCurvePoint]:
    """Generate 0..8h normal vs food-interfered efficacy curve points for Member 3 charts."""
    # Smooth log-normal / gamma-like plasma absorption curve peaking at 100%
    def _curve_val(t: float, tmax: float, peak: float) -> float:
        if t <= 0.0:
            return 0.0
        ratio = t / max(0.3, tmax)
        val = peak * ratio * math.exp(1.0 - ratio)
        return round(max(0.0, val), 2)

    if bioavailability_drop_pct >= 0:
        interfered_peak = max(12.0, 100.0 - bioavailability_drop_pct)
    else:
        # Negative drop indicates CYP3A4 inhibition / excessive serum accumulation
        interfered_peak = 100.0 + abs(bioavailability_drop_pct)

    interfered_tmax = base_tmax_hours + max(0.0, t_max_delay_hours)
    points: list[AbsorptionCurvePoint] = []
    for step in range(17):
        t_hr = step * 0.5
        points.append(
            AbsorptionCurvePoint(
                time_hours=t_hr,
                normal_efficacy_pct=_curve_val(t_hr, base_tmax_hours, 100.0),
                interfered_efficacy_pct=_curve_val(t_hr, interfered_tmax, interfered_peak),
            )
        )
    return points


def _expand_food_terms(food_items: list[str]) -> list[str]:
    expanded: list[str] = []
    for item in food_items:
        clean = item.strip()
        if not clean:
            continue
        expanded.append(clean)
        for alias in _FOOD_ID_TO_ALIASES.get(clean.lower(), []):
            expanded.append(alias)
    return expanded


def _plain_language_summary(
    salt: str,
    foods: list[str],
    rule: dict[str, Any],
) -> str:
    impact = rule["absorption_impact"]
    drop = float(impact["bioavailability_drop_pct"])
    gap = rule["safe_time_gap_hours"]
    foods_txt = ", ".join(foods) if foods else "certain meal items"
    if drop > 0:
        effect_txt = f"can reduce {salt} absorption by about {drop:.0f}%"
    elif drop < 0:
        effect_txt = f"can raise {salt} blood levels by about {abs(drop):.0f}% (higher side-effect risk)"
    else:
        effect_txt = f"can interfere with {salt} effectiveness"

    before_h = float(gap["before_food_hours"])
    after_h = float(gap["after_food_hours"])
    if before_h == 0.0 and after_h == 0.0:
        gap_txt = "Keep intake of these leafy greens steady day to day rather than sudden large swings."
    elif after_h > 0 and before_h == 0.0:
        gap_txt = "Take this tablet with or right after food to prevent stomach upset."
    else:
        gap_txt = f"Space {salt} at least {before_h:g}h before or {after_h:g}h after {foods_txt}."
    return f"Taking {salt} alongside {foods_txt} {effect_txt}. {gap_txt}"


def evaluate_conflicts(
    active_salts: list[str],
    food_items: list[str],
    rules: list[dict[str, Any]],
    nutrient_flags: list[str] | None = None,
    dose_time_hhmm: str | None = None,
) -> list[ConflictMatch]:
    """Deterministically evaluate food-drug conflicts against Member 2 verified rules."""
    expanded_foods = _expand_food_terms(food_items)
    nutrient_set = {n.strip().lower() for n in (nutrient_flags or []) if n.strip()}
    matches: list[ConflictMatch] = []
    seen_pairs: set[tuple[str, str]] = set()

    for salt in active_salts:
        salt_clean = salt.strip()
        salt_lower = salt_clean.lower()
        if not salt_lower:
            continue

        for rule in rules:
            rule_salts = [s.lower() for s in rule["active_salts"]]
            if not any(salt_lower in rs or rs in salt_lower for rs in rule_salts):
                continue

            pair_key = (rule["rule_id"], salt_lower)
            if pair_key in seen_pairs:
                continue

            # 1. Food intersection matching Member 2 culprit_indian_foods
            conflicted_foods: list[str] = []
            for user_food in expanded_foods:
                uf_lower = user_food.lower()
                for culprit in rule["culprit_indian_foods"]:
                    c_lower = culprit.lower()
                    if uf_lower in c_lower or c_lower in uf_lower:
                        # Prefer original readable name if user provided one
                        display = user_food if user_food in food_items else culprit
                        if display not in conflicted_foods:
                            conflicted_foods.append(display)
                        break

            # 2. Nutrient intersection matching Member 1 nutrient flags
            matched_nutrients: list[str] = []
            rule_nuts_lower = [rn.lower() for rn in rule["interfering_nutrients"]]
            for flag in nutrient_set:
                synonyms = _NUTRIENT_SYNONYMS.get(flag, {flag})
                for rn in rule["interfering_nutrients"]:
                    rn_l = rn.lower()
                    if rn_l in synonyms or any(syn in rn_l for syn in synonyms):
                        if rn not in matched_nutrients:
                            matched_nutrients.append(rn)

            if not conflicted_foods and not matched_nutrients:
                continue

            seen_pairs.add(pair_key)
            if not matched_nutrients:
                matched_nutrients = list(rule["interfering_nutrients"])

            earliest_meal = None
            if dose_time_hhmm:
                before_h = float(rule["safe_time_gap_hours"]["before_food_hours"])
                if before_h > 0:
                    dt = datetime.strptime(dose_time_hhmm, "%H:%M") + timedelta(hours=before_h)
                    earliest_meal = dt.strftime("%H:%M")

            swaps = [
                GharKiRasoiSwap(
                    culprit=s["culprit"],
                    substitute=s["substitute"],
                    dietary_rationale=s["dietary_rationale"],
                )
                for s in rule.get("ghar_ki_rasoi_swaps", [])
            ]
            curve = build_pharmacokinetic_curve(
                bioavailability_drop_pct=float(rule["absorption_impact"]["bioavailability_drop_pct"]),
                t_max_delay_hours=float(rule["absorption_impact"]["t_max_delay_hours"]),
            )

            matches.append(
                ConflictMatch(
                    rule_id=rule["rule_id"],
                    matched_salt=salt_clean,
                    drug_class=rule["drug_class"],
                    severity=rule["severity"],
                    conflicted_foods=conflicted_foods or list(food_items),
                    matched_nutrients=matched_nutrients,
                    interaction_type=rule.get("interaction_type", ""),
                    biochemical_mechanism=rule.get("biochemical_mechanism") or rule.get("interaction_type", ""),
                    plain_language_summary=_plain_language_summary(
                        salt_clean, conflicted_foods or food_items, rule
                    ),
                    safe_time_gap_hours=rule["safe_time_gap_hours"],
                    absorption_impact=rule["absorption_impact"],
                    ifct_evidence=rule.get("ifct_evidence", []),
                    ghar_ki_rasoi_swaps=swaps,
                    citations=rule.get("citations", []),
                    clinical_sign_off=rule.get("clinical_sign_off", {}),
                    recommended_earliest_meal_time=earliest_meal,
                    absorption_curve=curve,
                )
            )

    severity_rank = {"HIGH": 0, "MODERATE": 1, "LOW": 2}
    matches.sort(key=lambda m: (severity_rank.get(m.severity, 3), m.rule_id))
    return matches
