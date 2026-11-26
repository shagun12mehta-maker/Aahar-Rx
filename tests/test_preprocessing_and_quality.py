"""Tests for OpenCV image quality inspection, retry guidance, and curved/glare recovery."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from aahar_scan.preprocessing import (
    decode_image_bytes,
    enhance_strip_variants,
    inspect_image_quality,
    rotate_image,
)
from fixtures.generate_test_assets import generate_meal_image_bytes, generate_strip_image_bytes


def test_decode_rejects_empty_and_corrupt_bytes() -> None:
    with pytest.raises(ValueError):
        decode_image_bytes(b"")
    with pytest.raises(ValueError):
        decode_image_bytes(b"not-a-valid-image-payload")


def test_quality_gate_accepts_clean_and_recoverable_strips() -> None:
    for case_id in (
        "01_thyronorm_clean",
        "02_glycomet_curved_foil",
        "03_shelcal_glare",
        "04_ciplox_low_contrast",
        "05_orofer_dark_foil",
        "14_amlong_low_light_recoverable",
    ):
        bgr = decode_image_bytes(generate_strip_image_bytes(case_id))
        report = inspect_image_quality(bgr, mode="strip")
        assert report.passed is True, f"Expected pass for {case_id}, got issues={report.issues}"


def test_quality_gate_rejects_severe_blur_dark_glare_with_guidance() -> None:
    blur_report = inspect_image_quality(
        decode_image_bytes(generate_strip_image_bytes("15_fail_severe_blur")), mode="strip"
    )
    assert blur_report.passed is False
    assert "motion_or_focus_blur" in blur_report.issues
    assert any("blur" in msg.lower() for msg in blur_report.retry_guidance)

    dark_report = inspect_image_quality(
        decode_image_bytes(generate_strip_image_bytes("16_fail_severe_dark")), mode="strip"
    )
    assert dark_report.passed is False
    assert "low_light" in dark_report.issues
    assert any("dark" in msg.lower() for msg in dark_report.retry_guidance)

    glare_report = inspect_image_quality(
        decode_image_bytes(generate_strip_image_bytes("17_fail_severe_glare")), mode="strip"
    )
    assert glare_report.passed is False
    assert "specular_glare" in glare_report.issues
    assert any("glare" in msg.lower() for msg in glare_report.retry_guidance)


def test_meal_quality_gate_rejects_blur_and_dark() -> None:
    thali = inspect_image_quality(
        decode_image_bytes(generate_meal_image_bytes("thali_palak_dal_curd")), mode="meal"
    )
    assert thali.passed is True

    blur_meal = inspect_image_quality(
        decode_image_bytes(generate_meal_image_bytes("meal_severe_blur")), mode="meal"
    )
    assert blur_meal.passed is False
    assert "motion_or_focus_blur" in blur_meal.issues

    dark_meal = inspect_image_quality(
        decode_image_bytes(generate_meal_image_bytes("meal_severe_dark")), mode="meal"
    )
    assert dark_meal.passed is False
    assert "low_light" in dark_meal.issues


def test_enhancement_improves_low_contrast_foil_contrast() -> None:
    low_c = decode_image_bytes(generate_strip_image_bytes("04_ciplox_low_contrast"))
    raw_std = float(np.std(cv2.cvtColor(low_c, cv2.COLOR_BGR2GRAY)))

    variants, steps = enhance_strip_variants(low_c)
    assert "curved_foil_illumination_flatten" in steps
    assert "clahe_contrast_boost" in steps
    enh_std = float(np.std(cv2.cvtColor(variants["enhanced_clahe"], cv2.COLOR_BGR2GRAY)))
    assert enh_std > raw_std * 1.3

    rot90 = rotate_image(low_c, 90)
    assert rot90.shape[:2] == (low_c.shape[1], low_c.shape[0])
