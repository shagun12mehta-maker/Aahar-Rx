"""
Aahar-Rx Conflict Engine & Timetable Generator
Deterministic pharmacokinetic evaluation using data/verified_rules.json
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.schemas.clinical import (
    ClinicalRule,
    ConflictDetail,
    SafeTimeGapHours,
    AbsorptionImpact,
    GharKiRasoiSwap,
    IFCTEvidence,
    TimetableMedicineInput,
    TimetableMealInput,
    TimetableEntry,
    SeverityLevel
)

class ConflictEngine:
    def __init__(self, rules_file_path: Optional[str] = None):
        if rules_file_path is None:
            # Resolve relative to project root
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            rules_file_path = os.path.join(base_dir, "data", "verified_rules.json")
        
        self.rules_file_path = rules_file_path
        self.rules: List[Dict[str, Any]] = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.rules_file_path):
            raise FileNotFoundError(f"Clinical rules file not found at: {self.rules_file_path}")
        with open(self.rules_file_path, mode="r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_conflicts(self, active_salt: str, food_items: List[str]) -> List[ConflictDetail]:
        """
        Scans an active pharmaceutical salt against a list of foods identified in the patient's meal.
        Performs case-insensitive, bi-directional partial matching.
        """
        matched_conflicts: List[ConflictDetail] = []
        active_salt_lower = active_salt.strip().lower()

        for rule in self.rules:
            # Match salt
            salt_match = None
            for s in rule.get("active_salts", []):
                if active_salt_lower in s.lower() or s.lower() in active_salt_lower:
                    salt_match = s
                    break

            if not salt_match:
                continue

            # Check for culprit food matches
            conflicted_foods = []
            for food in food_items:
                f_lower = food.strip().lower()
                for culprit in rule.get("culprit_indian_foods", []):
                    c_lower = culprit.lower()
                    if f_lower in c_lower or c_lower in f_lower or any(word in c_lower for word in f_lower.split() if len(word) > 3):
                        conflicted_foods.append(food)
                        break

            if conflicted_foods:
                # Deduplicate conflicted foods
                unique_conflicted = list(dict.fromkeys(conflicted_foods))
                
                safe_gap_dict = rule.get("safe_time_gap_hours", {})
                impact_dict = rule.get("absorption_impact", {})

                detail = ConflictDetail(
                    rule_id=rule["rule_id"],
                    drug_class=rule["drug_class"],
                    severity=SeverityLevel(rule["severity"]),
                    matched_salt=salt_match,
                    conflicted_foods=unique_conflicted,
                    interaction_type=rule["interaction_type"],
                    biochemical_mechanism=rule["biochemical_mechanism"],
                    safe_time_gap_hours=SafeTimeGapHours(
                        before_food_hours=float(safe_gap_dict.get("before_food_hours", 0.0)),
                        after_food_hours=float(safe_gap_dict.get("after_food_hours", 0.0))
                    ),
                    absorption_impact=AbsorptionImpact(
                        bioavailability_drop_pct=float(impact_dict.get("bioavailability_drop_pct", 0.0)),
                        t_max_delay_hours=float(impact_dict.get("t_max_delay_hours", 0.0))
                    ),
                    ghar_ki_rasoi_swaps=[
                        GharKiRasoiSwap(
                            culprit=swap["culprit"],
                            substitute=swap["substitute"],
                            dietary_rationale=swap["dietary_rationale"]
                        )
                        for swap in rule.get("ghar_ki_rasoi_swaps", [])
                    ],
                    ifct_evidence=[
                        IFCTEvidence(
                            food=ev["food"],
                            ifct_code=ev["ifct_code"],
                            primary_nutrient=ev["primary_nutrient"],
                            value=ev["value"],
                            clinical_note=ev["clinical_note"]
                        )
                        for ev in rule.get("ifct_evidence", [])
                    ]
                )
                matched_conflicts.append(detail)

        return matched_conflicts

    def generate_safe_timetable(
        self,
        medications: List[TimetableMedicineInput],
        meals: List[TimetableMealInput]
    ) -> List[TimetableEntry]:
        """
        Calculates safe medication administration timings by evaluating conflict windows
        with planned meals (before_food_hours and after_food_hours).
        """
        timetable_entries: List[TimetableEntry] = []

        for med in medications:
            conflicts_for_med: List[ConflictDetail] = []
            conflicting_meals: List[tuple] = [] # (meal, conflict_detail)

            for meal in meals:
                matched = self.evaluate_conflicts(med.active_salt, meal.food_items)
                for conf in matched:
                    conflicts_for_med.append(conf)
                    conflicting_meals.append((meal, conf))

            try:
                prescribed_dt = datetime.strptime(med.prescribed_time.strip(), "%H:%M")
            except ValueError:
                prescribed_dt = datetime.strptime("08:00", "%H:%M")

            calculated_dt = prescribed_dt
            adjustment_reasons: List[str] = []
            recommended_swaps: List[GharKiRasoiSwap] = []
            max_safe_gap: Optional[SafeTimeGapHours] = None

            if not conflicting_meals:
                adjustment_reasons.append("No clinical food-drug conflict detected. Prescribed time is safe.")
            else:
                for meal, conf in conflicting_meals:
                    recommended_swaps.extend(conf.ghar_ki_rasoi_swaps)
                    max_safe_gap = conf.safe_time_gap_hours

                    try:
                        meal_dt = datetime.strptime(meal.planned_time.strip(), "%H:%M")
                    except ValueError:
                        meal_dt = datetime.strptime("08:30", "%H:%M")

                    # Calculate conflict window around meal:
                    # [meal_dt - before_food_hours, meal_dt + after_food_hours]
                    window_start = meal_dt - timedelta(hours=conf.safe_time_gap_hours.before_food_hours)
                    window_end = meal_dt + timedelta(hours=conf.safe_time_gap_hours.after_food_hours)

                    # Check if prescribed time falls into the prohibited conflict zone
                    if window_start <= calculated_dt <= window_end:
                        # Recommend shift: preferably administer BEFORE food by before_food_hours,
                        # or defer until window_end
                        if conf.safe_time_gap_hours.before_food_hours > 0:
                            safe_shift = meal_dt - timedelta(hours=conf.safe_time_gap_hours.before_food_hours)
                            adjustment_reasons.append(
                                f"Conflict with {meal.meal_name} ({', '.join(conf.conflicted_foods)}). "
                                f"Shifted to {safe_shift.strftime('%H:%M')} ({conf.safe_time_gap_hours.before_food_hours}h before meal) "
                                f"to avoid {conf.absorption_impact.bioavailability_drop_pct}% bioavailability loss."
                            )
                            calculated_dt = safe_shift
                        else:
                            safe_shift = window_end
                            adjustment_reasons.append(
                                f"Conflict with {meal.meal_name} ({', '.join(conf.conflicted_foods)}). "
                                f"Shifted to {safe_shift.strftime('%H:%M')} ({conf.safe_time_gap_hours.after_food_hours}h after meal)."
                            )
                            calculated_dt = safe_shift
                    else:
                        adjustment_reasons.append(
                            f"Prescribed time ({med.prescribed_time}) satisfies safe gap from {meal.meal_name}."
                        )

            # Deduplicate swaps
            seen_swaps = set()
            unique_swaps = []
            for sw in recommended_swaps:
                if sw.culprit not in seen_swaps:
                    seen_swaps.add(sw.culprit)
                    unique_swaps.append(sw)

            entry = TimetableEntry(
                medicine_name=med.medicine_name,
                active_salt=med.active_salt,
                prescribed_time=med.prescribed_time,
                calculated_safe_time=calculated_dt.strftime("%H:%M"),
                timing_adjustment_reason=" | ".join(adjustment_reasons),
                conflicts_detected=[c.rule_id for c in conflicts_for_med],
                safe_time_gap_hours=max_safe_gap,
                recommended_swaps=unique_swaps
            )
            timetable_entries.append(entry)

        return timetable_entries

# Global engine instance
conflict_engine = ConflictEngine()
