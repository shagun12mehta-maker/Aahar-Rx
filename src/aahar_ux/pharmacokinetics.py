"""Pharmacokinetic absorption & pharmacodynamic efficacy curve generator for Member 3."""

from __future__ import annotations

import math
from typing import Any

BASELINE_TMAX_HOURS: dict[str, float] = {
    "RULE-THY-001": 2.0,
    "RULE-IRO-002": 2.0,
    "RULE-ANT-003": 1.5,
    "RULE-BLD-004": 3.0,
    "RULE-HTN-005": 4.5,
    "RULE-DIA-006": 2.5,
    "RULE-HYP-007": 1.25,
    "RULE-LIP-008": 1.5,
}


def _asym_oral_curve(
    t_hours: float,
    t_peak_hours: float,
    peak_pct: float,
    rise_exp: float = 2.0,
    ke_decay: float = 0.26,
) -> float:
    """Physiological asymmetric oral absorption-elimination curve peaking cleanly at t_peak_hours."""
    if t_hours <= 0.0:
        return 0.0
    t_p = max(0.25, t_peak_hours)
    rise = (t_hours / t_p) ** rise_exp
    decay = math.exp(-ke_decay * (t_hours - t_p))
    # Combine power-rise and fixed systemic clearance decay while ensuring peak equals peak_pct at t_p.
    raw = (t_hours**rise_exp) * math.exp(-(rise_exp / t_p) * t_hours)
    raw_peak = (t_p**rise_exp) * math.exp(-rise_exp)
    tail_blend = 0.65 * (raw / raw_peak) + 0.35 * min(1.0, rise) * min(1.35, decay)
    if t_hours <= t_p:
        norm = raw / raw_peak
    else:
        decay_post = math.exp(-ke_decay * (t_hours - t_p))
        norm = min(1.0, 0.55 * (raw / raw_peak) + 0.45 * decay_post)
    return max(0.0, peak_pct * norm)


def _trapezoidal_auc(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    total = 0.0
    for idx in range(1, len(xs)):
        total += 0.5 * (ys[idx - 1] + ys[idx]) * (xs[idx] - xs[idx - 1])
    return total


def build_pharmacokinetic_profile(
    rule: dict[str, Any],
    horizon_hours: float = 12.0,
    step_hours: float = 0.25,
) -> dict[str, Any]:
    """Build 12h normal vs food-interfered absorption curves strictly from Member 2 rule figures."""
    rule_id = rule["rule_id"]
    impact = rule["absorption_impact"]
    drop_pct = float(impact["bioavailability_drop_pct"])
    delay_h = float(impact["t_max_delay_hours"])

    baseline_tmax = BASELINE_TMAX_HOURS.get(rule_id, 2.0)
    interfered_tmax = round(baseline_tmax + delay_h, 2)

    # Positive drop_pct reduces absorption (e.g., 38% drop -> 62% peak).
    # Negative drop_pct in Member 2 rules denotes CYP3A4 overload elevation (e.g., -45% -> 145% peak).
    interfered_peak_pct = round(max(12.0, 100.0 - drop_pct), 1)
    is_elevation = drop_pct < 0.0

    steps = int(round(horizon_hours / step_hours)) + 1
    time_points = [round(i * step_hours, 2) for i in range(steps)]
    normal_curve = [round(_asym_oral_curve(t, baseline_tmax, 100.0), 2) for t in time_points]
    interfered_curve = [
        round(_asym_oral_curve(t, interfered_tmax, interfered_peak_pct), 2) for t in time_points
    ]

    normal_auc = _trapezoidal_auc(time_points, normal_curve)
    interfered_auc = _trapezoidal_auc(time_points, interfered_curve)
    auc_change_pct = round(((interfered_auc - normal_auc) / normal_auc) * 100.0, 1) if normal_auc > 0 else 0.0

    return {
        "rule_id": rule_id,
        "drug_class": rule["drug_class"],
        "active_salts": list(rule["active_salts"]),
        "severity": rule["severity"],
        "interaction_type": rule["interaction_type"],
        "curve_mode": "elevation_toxicity" if is_elevation else "absorption_drop",
        "baseline_tmax_hours": baseline_tmax,
        "interfered_tmax_hours": interfered_tmax,
        "t_max_delay_hours": delay_h,
        "bioavailability_drop_pct": drop_pct,
        "normal_peak_pct": 100.0,
        "interfered_peak_pct": interfered_peak_pct,
        "therapeutic_floor_pct": 70.0,
        "safety_ceiling_pct": 115.0,
        "auc_change_pct": auc_change_pct,
        "time_points_hours": time_points,
        "normal_series_pct": normal_curve,
        "interfered_series_pct": interfered_curve,
    }


def build_all_pharmacokinetic_profiles(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build pharmacokinetic curve dictionary keyed by rule_id for all Member 2 rules."""
    return {rule["rule_id"]: build_pharmacokinetic_profile(rule) for rule in rules}
