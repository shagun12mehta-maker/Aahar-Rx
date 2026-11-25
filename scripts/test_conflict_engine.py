"""
Aahar-Rx Reference Conflict Engine & Timetable Generator
Designed by Member 2 (Clinical Rules & Data) for Member 4 (Backend Integration)

Demonstrates how the backend REST APIs:
1. /check-conflict (salt + food query)
2. /generate-timetable (medicine timing + safe gap calculation)
can directly consume data/verified_rules.json without hardcoding logic.
"""

import json
import os
from datetime import datetime, timedelta

def load_verified_rules(json_path: str):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Rules file not found at: {json_path}")
    with open(json_path, mode="r", encoding="utf-8") as f:
        return json.load(f)

def check_conflict(active_salt: str, food_items: list, rules: list):
    """
    Scans a patient's active pharmaceutical salt against a list of foods identified in their meal.
    """
    matched_conflicts = []
    active_salt_lower = active_salt.strip().lower()

    for rule in rules:
        # Check if active salt matches any salt in the rule
        salt_match = any(active_salt_lower in s.lower() or s.lower() in active_salt_lower for s in rule["active_salts"])
        if not salt_match:
            continue

        # Check for food intersection
        conflicted_foods = []
        for food in food_items:
            f_lower = food.strip().lower()
            for culprit in rule["culprit_indian_foods"]:
                if f_lower in culprit.lower() or culprit.lower() in f_lower:
                    conflicted_foods.append(food)
                    break

        if conflicted_foods:
            matched_conflicts.append({
                "rule_id": rule["rule_id"],
                "drug_class": rule["drug_class"],
                "severity": rule["severity"],
                "conflicted_foods": conflicted_foods,
                "interaction_type": rule["interaction_type"],
                "biochemical_mechanism": rule["biochemical_mechanism"],
                "safe_gap": rule["safe_time_gap_hours"],
                "absorption_impact": rule["absorption_impact"],
                "kitchen_swaps": rule["ghar_ki_rasoi_swaps"],
                "citations": rule["citations"],
                "clinical_status": rule["clinical_sign_off"]["status"]
            })

    return matched_conflicts

def calculate_safe_schedule(medicine_name: str, medicine_time_str: str, conflict_result: dict):
    """
    Calculates exact safe time window for taking meals and medicines.
    Example: Medicine at 07:00 AM with Levothyroxine -> Chai safe at >= 08:00 AM.
    """
    med_time = datetime.strptime(medicine_time_str, "%H:%M")
    before_gap = conflict_result["safe_gap"]["before_food_hours"]
    after_gap = conflict_result["safe_gap"]["after_food_hours"]

    safe_food_earliest = med_time + timedelta(hours=before_gap)
    safe_med_after_food = med_time + timedelta(hours=after_gap)

    return {
        "medicine": medicine_name,
        "scheduled_intake": medicine_time_str,
        "food_restriction_window": f"{medicine_time_str} to {safe_food_earliest.strftime('%H:%M')}",
        "recommended_meal_time": safe_food_earliest.strftime("%I:%M %p"),
        "clinical_advice": f"Wait at least {before_gap} hour(s) after taking {medicine_name} before consuming {', '.join(conflict_result['conflicted_foods'])}."
    }

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rules_file = os.path.join(base_dir, "data", "verified_rules.json")

    rules = load_verified_rules(rules_file)
    print(f"[Aahar-Rx Engine] Loaded {len(rules)} verified clinical rules.\n")

    # TEST SCENARIO 1: Morning Thyroid Pill with Milky Chai
    test_salt_1 = "Levothyroxine Sodium"
    test_meal_1 = ["Morning Masala Chai with Milk", "Biscuits"]
    print(f"--- Scenario 1: Patient taking '{test_salt_1}' with meal: {test_meal_1} ---")
    conflicts_1 = check_conflict(test_salt_1, test_meal_1, rules)

    if conflicts_1:
        c = conflicts_1[0]
        print(f"🚨 [CONFLICT DETECTED - {c['severity']} SEVERITY]")
        print(f"   Reason: {c['biochemical_mechanism']}")
        print(f"   Bioavailability Impact: -{c['absorption_impact']['bioavailability_drop_pct']}%")
        schedule = calculate_safe_schedule(test_salt_1, "07:00", c)
        print(f"   Safe Window: {schedule['clinical_advice']}")
        print(f"   Suggested Swap: {c['kitchen_swaps'][0]['substitute']}\n")

    # TEST SCENARIO 2: Iron Supplement with Lunch Chai
    test_salt_2 = "Ferrous Ascorbate"
    test_meal_2 = ["Palak Paneer", "Masala Chai", "Roti"]
    print(f"--- Scenario 2: Patient taking '{test_salt_2}' with meal: {test_meal_2} ---")
    conflicts_2 = check_conflict(test_salt_2, test_meal_2, rules)

    if conflicts_2:
        c = conflicts_2[0]
        print(f"🚨 [CONFLICT DETECTED - {c['severity']} SEVERITY]")
        print(f"   Reason: {c['biochemical_mechanism']}")
        print(f"   Suggested Swap: {c['kitchen_swaps'][0]['substitute']}\n")
