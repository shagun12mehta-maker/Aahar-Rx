"""
Aahar-Rx Routine Shift Engine
Dynamically adjusts medication reminder alarms when meal routines are delayed (e.g. late breakfast).
Enforces clinical safety: shifts alarm timing only, never alters prescribed dosages.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from app.services.conflict_engine import conflict_engine

class RoutineShiftEngine:
    @classmethod
    def shift_alarm_for_delayed_meal(
        cls,
        medicine_name: str,
        active_salt: str,
        scheduled_time: str,
        meal_anchor: str,
        delayed_meal_time: str
    ) -> Dict[str, Any]:
        """
        Recalculates alarm timing when anchor meal is postponed.
        Example: Levothyroxine scheduled at 07:00 for 07:30 breakfast.
        If breakfast is delayed to 09:00:
        Option A: Keep pill at 07:00 (since > 1h before 09:00, still safe!).
        If meal was delayed and medicine was scheduled after-meal (e.g., Metformin after lunch at 13:00 delayed to 14:30),
        the post-meal medicine alarm shifts forward to 14:30.
        If medicine must precede meal by 1h and patient forgot to take it early:
        Pill shifts to delayed_meal - 1h.
        """
        sched_dt = datetime.strptime(scheduled_time.strip(), "%H:%M")
        meal_dt = datetime.strptime(delayed_meal_time.strip(), "%H:%M")

        # Check rule for this salt
        salt_rules = [
            r for r in conflict_engine.rules
            if any(active_salt.lower() in s.lower() for s in r.get("active_salts", [])) or
               (r.get("salt_name") and active_salt.lower() in r["salt_name"].lower())
        ]

        before_gap = 1.0
        after_gap = 2.0
        if salt_rules:
            safe_dict = salt_rules[0].get("safe_time_gap_hours", {})
            before_gap = float(safe_dict.get("before_food_hours", 1.0))
            after_gap = float(safe_dict.get("after_food_hours", 2.0))

        # Determine if medicine is typically taken before or after meal
        # If scheduled time is after or equal to planned anchor meal, shift after delayed meal
        # E.g. Metformin taken with or after meal
        if before_gap == 0.0 or sched_dt >= meal_dt:
            # Post-meal or with-meal medication
            new_alarm_dt = meal_dt
            shift_minutes = int((new_alarm_dt - sched_dt).total_seconds() / 60)
            shift_rationale = (
                f"{meal_anchor} delayed to {delayed_meal_time}. {medicine_name} must be taken with or "
                f"immediately after food. Alarm shifted to {new_alarm_dt.strftime('%H:%M')}."
            )
        else:
            # Pre-meal medication (e.g. Levothyroxine requiring 1h before meal)
            # If meal is delayed, the latest safe time is delayed_meal - before_gap
            latest_safe_time = meal_dt - timedelta(hours=before_gap)
            if sched_dt < latest_safe_time:
                # Can remain or slightly relax
                new_alarm_dt = sched_dt
                shift_minutes = 0
                shift_rationale = (
                    f"{meal_anchor} delayed to {delayed_meal_time}. Your {medicine_name} at "
                    f"{scheduled_time} remains safe (leaves {before_gap}h before food)."
                )
            else:
                new_alarm_dt = latest_safe_time
                shift_minutes = int((new_alarm_dt - sched_dt).total_seconds() / 60)
                shift_rationale = (
                    f"{meal_anchor} delayed to {delayed_meal_time}. {medicine_name} requires at least "
                    f"{before_gap}h before eating. Alarm adjusted to {new_alarm_dt.strftime('%H:%M')}."
                )

        fcm_payload = {
            "title": f"Aahar-Rx Routine Shift: {medicine_name}",
            "body": f"Your alarm was adjusted to {new_alarm_dt.strftime('%H:%M')} due to delayed {meal_anchor}.",
            "data": {
                "medicine_name": medicine_name,
                "active_salt": active_salt,
                "new_alarm_time": new_alarm_dt.strftime("%H:%M"),
                "shift_minutes": shift_minutes,
                "type": "ROUTINE_ALARM_SHIFT"
            }
        }

        return {
            "medicine_name": medicine_name,
            "original_scheduled_time": scheduled_time,
            "meal_anchor": meal_anchor,
            "delayed_meal_time": delayed_meal_time,
            "shifted_alarm_time": new_alarm_dt.strftime("%H:%M"),
            "shift_minutes": shift_minutes,
            "shift_rationale": shift_rationale,
            "fcm_payload": fcm_payload
        }

routine_shift_engine = RoutineShiftEngine()
