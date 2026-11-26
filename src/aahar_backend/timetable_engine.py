"""Safe Time-Gap Timetable Generator and QR Health Pass builder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from .conflict_engine import evaluate_conflicts
from .models import (
    ConflictMatch,
    MealSlotInput,
    MedicationDoseInput,
    QrHealthPassPayload,
    TimetableEntry,
    TimetableResponse,
)


def _to_minutes(hhmm: str) -> int:
    dt = datetime.strptime(hhmm, "%H:%M")
    return dt.hour * 60 + dt.minute


def _from_minutes(total_mins: int) -> str:
    wrapped = total_mins % (24 * 60)
    return f"{wrapped // 60:02d}:{wrapped % 60:02d}"


def generate_safe_timetable(
    user_id: str,
    consent_id: str,
    medications: list[MedicationDoseInput],
    meals: list[MealSlotInput],
    rules: list[dict[str, Any]],
) -> TimetableResponse:
    """Compute a conflict-resolved daily medicine & meal timetable + QR Health Pass."""
    all_conflicts: list[ConflictMatch] = []
    seen_conflict_keys: set[tuple[str, str]] = set()

    meal_adjustments: dict[int, list[tuple[int, str, list[str], str]]] = {}
    med_adjustments: dict[int, list[tuple[int, str, str, list[str], list[str]]]] = {}

    for med_idx, med in enumerate(medications):
        med_min = _to_minutes(med.preferred_time_hhmm)

        for meal_idx, meal in enumerate(meals):
            conflicts = evaluate_conflicts(
                active_salts=[med.active_salt],
                food_items=meal.food_items,
                rules=rules,
                nutrient_flags=meal.nutrient_flags,
                dose_time_hhmm=med.preferred_time_hhmm,
            )
            if not conflicts:
                continue

            for c in conflicts:
                ck = (c.rule_id, meal.meal_slot)
                if ck not in seen_conflict_keys:
                    seen_conflict_keys.add(ck)
                    all_conflicts.append(c)

                before_mins = int(round(float(c.safe_time_gap_hours["before_food_hours"]) * 60))
                after_mins = int(round(float(c.safe_time_gap_hours["after_food_hours"]) * 60))
                swaps = [s.substitute for s in c.ghar_ki_rasoi_swaps]
                meal_min = _to_minutes(meal.time_hhmm)

                # Case A: Consistency advisory (e.g., Warfarin + Vitamin K: before=0, after=0)
                if before_mins == 0 and after_mins == 0:
                    med_adjustments.setdefault(med_idx, []).append(
                        (
                            med_min,
                            "consistency_advisory",
                            f"Maintain steady daily Vitamin K intake; avoid sudden heavy boluses in {meal.meal_slot}.",
                            [c.rule_id],
                            swaps,
                        )
                    )
                    continue

                # Case B: Take with/right after food buffer (e.g., Metformin: before=0, after=0.1h)
                if before_mins == 0 and after_mins > 0 and after_mins <= 30:
                    target_min = meal_min + after_mins
                    med_adjustments.setdefault(med_idx, []).append(
                        (
                            target_min,
                            "take_with_meal_buffer",
                            f"Take {med.medicine_label} with or right after {meal.meal_slot} ({_from_minutes(target_min)}) to prevent GI upset.",
                            [c.rule_id],
                            swaps,
                        )
                    )
                    continue

                # Case C: Time-gap separation needed around conflicting meal
                # If medication is morning empty-stomach (<08:30) and meal is early morning/breakfast soon after,
                # push the conflicting food slot forward to med_min + before_mins.
                if med_min <= meal_min and (meal_min - med_min) < before_mins:
                    if meal.meal_slot in ("early_morning_empty_stomach", "breakfast", "mid_morning"):
                        safe_meal_min = med_min + before_mins
                        meal_adjustments.setdefault(meal_idx, []).append(
                            (
                                safe_meal_min,
                                f"Delayed after {med.medicine_label} ({before_mins / 60:.1f}h safe gap): "
                                f"move {meal.meal_slot} to {_from_minutes(safe_meal_min)} or use swap.",
                                [c.rule_id],
                                swaps[0] if swaps else "",
                            )
                        )
                    else:
                        # Shift medication earlier (meal_min - before_mins) or after (meal_min + after_mins)
                        safe_after = meal_min + after_mins
                        med_adjustments.setdefault(med_idx, []).append(
                            (
                                safe_after,
                                "shifted_for_safe_gap",
                                f"Space {med.medicine_label} {after_mins / 60:.1f}h after {meal.meal_slot} "
                                f"({_from_minutes(safe_after)}) to avoid chelation/inhibition.",
                                [c.rule_id],
                                swaps,
                            )
                        )
                elif meal_min < med_min and (med_min - meal_min) < after_mins:
                    safe_after = meal_min + after_mins
                    med_adjustments.setdefault(med_idx, []).append(
                        (
                            safe_after,
                            "shifted_for_safe_gap",
                            f"Wait {after_mins / 60:.1f}h after {meal.meal_slot} before taking {med.medicine_label} ({_from_minutes(safe_after)}).",
                            [c.rule_id],
                            swaps,
                        )
                    )

    timeline: list[TimetableEntry] = []

    for med_idx, med in enumerate(medications):
        orig_min = _to_minutes(med.preferred_time_hhmm)
        adjs = med_adjustments.get(med_idx, [])
        if not adjs:
            timeline.append(
                TimetableEntry(
                    entry_type="medication",
                    label=f"{med.medicine_label} ({med.active_salt})",
                    original_time_hhmm=med.preferred_time_hhmm,
                    recommended_time_hhmm=med.preferred_time_hhmm,
                    adjusted_minutes=0,
                    status="safe_as_planned",
                    guidance=f"No meal timing conflicts detected; take {med.medicine_label} as prescribed at {med.preferred_time_hhmm}.",
                )
            )
        else:
            # Pick the most protective later safe time if multiple rules trigger, or advisory
            target_min = max(a[0] for a in adjs)
            status = adjs[0][1]
            for _, st, _, _, _ in adjs:
                if st in ("shifted_for_safe_gap", "take_with_meal_buffer"):
                    status = st
                    break
            all_rids = sorted({rid for a in adjs for rid in a[3]})
            all_swaps = list(dict.fromkeys(sw for a in adjs for sw in a[4] if sw))
            timeline.append(
                TimetableEntry(
                    entry_type="medication",
                    label=f"{med.medicine_label} ({med.active_salt})",
                    original_time_hhmm=med.preferred_time_hhmm,
                    recommended_time_hhmm=_from_minutes(target_min),
                    adjusted_minutes=target_min - orig_min,
                    status=status,  # type: ignore[arg-type]
                    guidance=" ".join(dict.fromkeys(a[2] for a in adjs)),
                    rule_ids=all_rids,
                    kitchen_swaps=all_swaps,
                )
            )

    for meal_idx, meal in enumerate(meals):
        orig_min = _to_minutes(meal.time_hhmm)
        adjs = meal_adjustments.get(meal_idx, [])
        if not adjs:
            timeline.append(
                TimetableEntry(
                    entry_type="meal",
                    label=f"{meal.meal_slot}: {', '.join(meal.food_items)}",
                    original_time_hhmm=meal.time_hhmm,
                    recommended_time_hhmm=meal.time_hhmm,
                    adjusted_minutes=0,
                    status="safe_as_planned",
                    guidance=f"Meal slot '{meal.meal_slot}' has no timing shift required.",
                )
            )
        else:
            target_min = max(a[0] for a in adjs)
            rids = sorted({rid for a in adjs for rid in a[2]})
            swaps = list(dict.fromkeys(a[3] for a in adjs if a[3]))
            timeline.append(
                TimetableEntry(
                    entry_type="meal",
                    label=f"{meal.meal_slot}: {', '.join(meal.food_items)}",
                    original_time_hhmm=meal.time_hhmm,
                    recommended_time_hhmm=_from_minutes(target_min),
                    adjusted_minutes=target_min - orig_min,
                    status="shifted_for_safe_gap",
                    guidance=" ".join(dict.fromkeys(a[1] for a in adjs)),
                    rule_ids=rids,
                    kitchen_swaps=swaps,
                )
            )

    timeline.sort(key=lambda entry: _to_minutes(entry.recommended_time_hhmm))

    schedule_id = f"sched_{uuid.uuid4().hex[:12]}"
    all_swaps_flat = list(
        dict.fromkeys(
            s.substitute
            for c in all_conflicts
            for s in c.ghar_ki_rasoi_swaps
        )
    )
    qr_payload = QrHealthPassPayload(
        schedule_id=schedule_id,
        active_salts=sorted({m.active_salt for m in medications}),
        safe_daily_summary=[
            f"{e.recommended_time_hhmm} - {e.label} ({e.status})" for e in timeline
        ],
        key_kitchen_swaps=all_swaps_flat[:4],
    )

    return TimetableResponse(
        schedule_id=schedule_id,
        user_id=user_id,
        consent_id=consent_id,
        conflict_count=len(all_conflicts),
        detected_conflicts=all_conflicts,
        timeline=timeline,
        qr_health_pass=qr_payload,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
