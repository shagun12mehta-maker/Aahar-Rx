"""Tests for Member 3 localization (EN/HI/MR), PK curves, voice audio, and heydamir/unslop rules."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from aahar_ux import (
    SUPPORTED_LANGUAGES,
    UI_TRANSLATIONS,
    build_all_pharmacokinetic_profiles,
    build_voice_scripts_for_rules,
    validate_translation_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
RULES = json.loads((ROOT / "data" / "verified_rules.json").read_text(encoding="utf-8"))

_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def _hex_to_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = _hex_to_luminance(fg_hex)
    l2 = _hex_to_luminance(bg_hex)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def test_trilingual_translations_complete_clean_and_no_emojis() -> None:
    errors = validate_translation_bundle(UI_TRANSLATIONS)
    assert errors == []

    exported = json.loads((FRONTEND / "data" / "i18n.json").read_text(encoding="utf-8"))
    assert set(exported.keys()) == set(SUPPORTED_LANGUAGES)
    assert validate_translation_bundle(exported) == []


def test_pharmacokinetic_curves_match_all_8_member2_rules() -> None:
    profiles = build_all_pharmacokinetic_profiles(RULES)
    assert len(profiles) == len(RULES) == 8

    for rule in RULES:
        rid = rule["rule_id"]
        prof = profiles[rid]
        drop_pct = float(rule["absorption_impact"]["bioavailability_drop_pct"])
        delay_h = float(rule["absorption_impact"]["t_max_delay_hours"])

        assert len(prof["time_points_hours"]) == 49
        assert prof["normal_peak_pct"] == 100.0
        assert prof["t_max_delay_hours"] == delay_h
        assert abs(max(prof["normal_series_pct"]) - 100.0) < 0.01

        expected_peak = round(100.0 - drop_pct, 1)
        assert abs(prof["interfered_peak_pct"] - expected_peak) < 0.01
        assert abs(max(prof["interfered_series_pct"]) - expected_peak) < 1.5

        if drop_pct < 0:
            assert prof["curve_mode"] == "elevation_toxicity"
            assert prof["interfered_peak_pct"] > prof["safety_ceiling_pct"]
        else:
            assert prof["curve_mode"] == "absorption_drop"


def test_trilingual_voice_scripts_and_synthesized_mp3_files() -> None:
    scripts = build_voice_scripts_for_rules(RULES)
    assert len(scripts) == 8

    for rid, entry in scripts.items():
        for lang in SUPPORTED_LANGUAGES:
            meta = entry["languages"][lang]
            assert len(meta["text"]) >= 80
            assert "!" not in meta["text"]
            assert not _EMOJI_RE.search(meta["text"])
            if lang in ("hi", "mr"):
                assert re.search(r"[\u0900-\u097F]", meta["text"])

            mp3_path = FRONTEND / meta["audio_rel_path"]
            assert mp3_path.exists(), f"Missing audio asset: {mp3_path}"
            assert mp3_path.stat().st_size > 10_000, f"Audio asset too small: {mp3_path}"


def test_unslop_design_discipline_and_wcag_contrast() -> None:
    tokens_css = (FRONTEND / "css" / "tokens.css").read_text(encoding="utf-8")
    app_css = (FRONTEND / "css" / "app.css").read_text(encoding="utf-8")

    for css_text in (tokens_css, app_css):
        assert "linear-gradient" not in css_text
        assert "radial-gradient" not in css_text
        assert "conic-gradient" not in css_text
        assert "backdrop-filter" not in css_text
        assert "animate-pulse" not in css_text
        assert "transition: all" not in css_text
        assert not re.search(r"font-weight:\s*(?:700|800|900)", css_text)
        assert "cubic-bezier(0.22, 1, 0.36, 1)" in tokens_css

    # Check WCAG >= 4.5:1 contrast on primary text, muted text, and botanical accent CTA.
    assert _contrast_ratio("#1f1b16", "#fdfbf7") >= 12.0
    assert _contrast_ratio("#534a40", "#fdfbf7") >= 7.0
    assert _contrast_ratio("#6c6358", "#fdfbf7") >= 4.9
    assert _contrast_ratio("#ffffff", "#166534") >= 6.5
    assert _contrast_ratio("#b42318", "#fdfbf7") >= 5.5

    # Verify zero emojis or forbidden AI filler copy in custom frontend JS/HTML sources.
    for path in list((FRONTEND / "js").rglob("*.js")) + [FRONTEND / "index.html"]:
        content = path.read_text(encoding="utf-8")
        assert not _EMOJI_RE.search(content), f"Emoji found in {path}"
        for banned in ("supercharge", "revolutionize", "game-changing", "Welcome back"):
            assert banned.lower() not in content.lower(), f"Banned slop phrase {banned} in {path}"


def test_member3_offline_vendor_and_pwa_assets_present() -> None:
    required = [
        FRONTEND / "index.html",
        FRONTEND / "manifest.webmanifest",
        FRONTEND / "sw.js",
        FRONTEND / "vendor" / "react.production.min.js",
        FRONTEND / "vendor" / "react-dom.production.min.js",
        FRONTEND / "vendor" / "htm.umd.js",
        FRONTEND / "vendor" / "chart.umd.min.js",
        FRONTEND / "vendor" / "qrcode.min.js",
        FRONTEND / "data" / "i18n.json",
        FRONTEND / "data" / "pk_profiles.json",
        FRONTEND / "data" / "rules_bundle.json",
        FRONTEND / "data" / "voice_scripts.json",
    ]
    for fpath in required:
        assert fpath.exists() and fpath.stat().st_size > 100
