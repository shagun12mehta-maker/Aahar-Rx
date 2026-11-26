"""Tests for multi-engine Strip OCR, OCR error correction, 17-strip benchmark, and manual fallback."""

from __future__ import annotations

import pytest

from aahar_scan.ocr_engines import RapidOcrEngine, SmartStripOcrPipeline, WindowsNativeOcrEngine
from aahar_scan.preprocessing import decode_image_bytes
from aahar_scan.salt_resolver import SaltResolver, extract_strength
from fixtures.generate_test_assets import STRIP_SPECS, generate_strip_image_bytes


def test_ocr_noise_normalization_and_strength_extraction() -> None:
    resolver = SaltResolver()

    meds, fallback = resolver.resolve_from_ocr_text("THYRONORM5OMCG LEV0THYR0X1NE")
    assert not fallback
    assert meds[0].brand_name == "Thyronorm"
    assert meds[0].active_salts == ["Levothyroxine Sodium"]
    assert meds[0].drug_class == "thyroid"
    assert meds[0].strength_text == "50 mcg"

    gly, _ = resolver.resolve_from_ocr_text("GLYC0MET 500 SR")
    assert gly[0].brand_name == "Glycomet"
    assert "Metformin Hydrochloride" in gly[0].active_salts

    cip, _ = resolver.resolve_from_ocr_text("C1PLOX 500 MG TABLETS IP")
    assert cip[0].brand_name == "Ciplox"
    assert cip[0].active_salts == ["Ciprofloxacin"]
    assert extract_strength("AUGMENTIN 625 DUO 500 mg + 125 mg") == "500 mg + 125 mg"


def test_brand_directory_covers_core_drug_classes() -> None:
    resolver = SaltResolver()
    classes = {e["drug_class"] for e in resolver.entries}
    for expected in (
        "thyroid",
        "diabetes",
        "blood_pressure",
        "anaemia_supplement",
        "antibiotic",
        "anticoagulant",
        "statin",
        "gastric_ppi",
        "diuretic",
        "bone_health",
    ):
        assert expected in classes


def test_manual_brand_and_salt_search_fallback() -> None:
    resolver = SaltResolver()

    by_salt = resolver.search_brands_and_salts("warfarin")
    assert any(hit.brand_name == "Warf" for hit in by_salt)

    by_typo = resolver.search_brands_and_salts("thironorm")
    assert by_typo[0].brand_name == "Thyronorm"

    by_regional = resolver.search_brands_and_salts("ferro")
    assert any(hit.brand_name == "Ferro-XT" and hit.is_regional_brand for hit in by_regional)

    manual_med = resolver.build_manual_medication(
        "shelcal", strength_text="500 mg + 250 IU", intended_dose_time_hhmm="09:00"
    )
    assert manual_med.resolution_source == "manual_fallback"
    assert manual_med.confirmed_by_user is True
    assert manual_med.confidence == 1.0
    assert manual_med.intended_dose_time_hhmm == "09:00"


@pytest.mark.parametrize("spec", [s for s in STRIP_SPECS if s.should_pass_quality], ids=lambda s: s.case_id)
def test_end_to_end_strip_pipeline_all_14_recoverable_strips(spec) -> None:
    pipeline = SmartStripOcrPipeline(primary_engine=RapidOcrEngine())
    img_bytes = generate_strip_image_bytes(spec.case_id)
    res = pipeline.scan_bytes(img_bytes, scan_id=f"test_{spec.case_id}")

    assert res.retry_required is False, f"{spec.case_id} triggered unexpected retry: {res.quality_report.issues}"
    assert res.resolved_medications, f"{spec.case_id} failed to resolve any medication; raw='{res.raw_text}'"
    top = res.resolved_medications[0]
    assert spec.expected_salt in top.active_salts, (
        f"{spec.case_id}: expected salt {spec.expected_salt}, got {top.active_salts} (raw='{res.raw_text}')"
    )
    assert top.drug_class == spec.expected_drug_class


@pytest.mark.parametrize("spec", [s for s in STRIP_SPECS if not s.should_pass_quality], ids=lambda s: s.case_id)
def test_end_to_end_strip_pipeline_rejects_unreadable_photos(spec) -> None:
    pipeline = SmartStripOcrPipeline(primary_engine=RapidOcrEngine())
    img_bytes = generate_strip_image_bytes(spec.case_id)
    res = pipeline.scan_bytes(img_bytes, scan_id=f"test_{spec.case_id}")

    assert res.retry_required is True
    assert res.needs_manual_fallback is True
    assert len(res.quality_report.retry_guidance) >= 1
    assert len(res.manual_suggestions) >= 1


def test_windows_native_ocr_comparative_backend() -> None:
    win_ocr = WindowsNativeOcrEngine()
    if not win_ocr.is_available():
        pytest.skip("Windows native OCR unavailable on non-Windows host")
    attempt = win_ocr.recognize(
        decode_image_bytes(generate_strip_image_bytes("01_thyronorm_clean")),
        variant_name="raw",
    )
    assert "THYRONORM" in attempt.raw_text.upper()
