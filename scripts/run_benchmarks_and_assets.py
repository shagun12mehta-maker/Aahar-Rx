"""Run Day 1 OCR engine comparison, Day 4 17-strip benchmark, and Day 6 pitch visuals."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import textwrap
import time

import cv2
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from aahar_scan.constants import CLINICAL_SAFETY_DISCLAIMER, DATA_DIR  # noqa: E402
from aahar_scan.meal_vision import MealVisionService  # noqa: E402
from aahar_scan.member2_handoff import (  # noqa: E402
    check_member2_rule_compatibility,
    load_member2_verified_rules,
)
from aahar_scan.models import MealConfirmationUpdate  # noqa: E402
from aahar_scan.ocr_engines import (  # noqa: E402
    RapidOcrEngine,
    SmartStripOcrPipeline,
    TesseractOcrEngine,
    WindowsNativeOcrEngine,
    get_available_engines,
)
from aahar_scan.pipeline import AaharSmartScanPipeline, create_scan_consent  # noqa: E402
from aahar_scan.preprocessing import decode_image_bytes, enhance_strip_variants  # noqa: E402
from fixtures.generate_test_assets import (  # noqa: E402
    STRIP_SPECS,
    generate_meal_image_bytes,
    generate_strip_image_bytes,
)

REPORTS_DIR = PROJECT_ROOT / "reports"


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def run_day1_engine_comparison() -> dict:
    """Compare available OCR engines (raw vs OpenCV enhanced) on challenging strip subsets."""
    subset_ids = [
        "01_thyronorm_clean",
        "02_glycomet_curved_foil",
        "03_shelcal_glare",
        "04_ciplox_low_contrast",
        "05_orofer_dark_foil",
        "06_warf_rotated_90",
        "12_ferro_xt_regional_glare",
        "14_amlong_low_light_recoverable",
    ]
    spec_by_id = {s.case_id: s for s in STRIP_SPECS}
    engines = get_available_engines()
    tesseract_available = TesseractOcrEngine().is_available()

    pipeline = SmartStripOcrPipeline(primary_engine=RapidOcrEngine())
    per_engine_stats: dict[str, dict] = {
        e.name: {
            "raw_salt_hits": 0,
            "enhanced_salt_hits": 0,
            "total": len(subset_ids),
            "raw_latencies_ms": [],
            "enhanced_latencies_ms": [],
            "cases": {},
        }
        for e in engines
    }

    for cid in subset_ids:
        spec = spec_by_id[cid]
        img_bytes = generate_strip_image_bytes(cid)
        comp = pipeline.benchmark_engines_on_image(img_bytes, engines=engines)
        for eng_name, res in comp.items():
            raw_hit = spec.expected_salt in res["raw"]["resolved_salts"]
            enh_hit = spec.expected_salt in res["enhanced"]["resolved_salts"]
            st = per_engine_stats[eng_name]
            st["raw_salt_hits"] += int(raw_hit)
            st["enhanced_salt_hits"] += int(enh_hit)
            st["raw_latencies_ms"].append(res["raw"]["latency_ms"])
            st["enhanced_latencies_ms"].append(res["enhanced"]["latency_ms"])
            st["cases"][cid] = {
                "condition": spec.condition,
                "raw_hit": raw_hit,
                "enhanced_hit": enh_hit,
                "raw_text": res["raw"]["raw_text"],
                "enhanced_text": res["enhanced"]["raw_text"],
                "raw_ms": res["raw"]["latency_ms"],
                "enhanced_ms": res["enhanced"]["latency_ms"],
            }

    summary = {}
    for eng_name, st in per_engine_stats.items():
        n = st["total"]
        summary[eng_name] = {
            "raw_accuracy_pct": round(100.0 * st["raw_salt_hits"] / n, 1),
            "enhanced_accuracy_pct": round(100.0 * st["enhanced_salt_hits"] / n, 1),
            "raw_salt_hits": st["raw_salt_hits"],
            "enhanced_salt_hits": st["enhanced_salt_hits"],
            "total_cases": n,
            "mean_raw_latency_ms": round(sum(st["raw_latencies_ms"]) / n, 1),
            "mean_enhanced_latency_ms": round(sum(st["enhanced_latencies_ms"]) / n, 1),
            "cases": st["cases"],
        }

    return {
        "engines_tested": [e.name for e in engines],
        "tesseract_installed_locally": tesseract_available,
        "windows_ocr_available": WindowsNativeOcrEngine().is_available(),
        "summary": summary,
    }


def run_day4_full_strip_benchmark() -> dict:
    """Run the full SmartStripOcrPipeline across all 17 strip fixtures."""
    pipeline = SmartStripOcrPipeline(primary_engine=RapidOcrEngine())
    rows: list[dict] = []

    recoverable_total = 0
    recoverable_passed = 0
    defect_total = 0
    defect_rejected_correctly = 0
    regional_total = 0
    regional_passed = 0

    for spec in STRIP_SPECS:
        t0 = time.perf_counter()
        res = pipeline.scan_bytes(generate_strip_image_bytes(spec.case_id), scan_id=f"bench_{spec.case_id}")
        total_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        top_med = res.resolved_medications[0] if res.resolved_medications else None
        salt_matched = bool(top_med and spec.expected_salt in top_med.active_salts)

        if spec.should_pass_quality:
            recoverable_total += 1
            if not res.retry_required and salt_matched:
                recoverable_passed += 1
            if spec.is_regional:
                regional_total += 1
                if not res.retry_required and salt_matched:
                    regional_passed += 1
        else:
            defect_total += 1
            if res.retry_required:
                defect_rejected_correctly += 1

        rows.append(
            {
                "case_id": spec.case_id,
                "condition": spec.condition,
                "is_regional": spec.is_regional,
                "should_pass_quality": spec.should_pass_quality,
                "retry_required": res.retry_required,
                "quality_issues": res.quality_report.issues,
                "blur_score": res.quality_report.blur_score,
                "glare_ratio": res.quality_report.glare_ratio,
                "mean_brightness": res.quality_report.mean_brightness,
                "expected_salt": spec.expected_salt,
                "resolved_brand": top_med.brand_name if top_med else None,
                "resolved_salts": top_med.active_salts if top_med else [],
                "resolution_source": top_med.resolution_source if top_med else None,
                "confidence": top_med.confidence if top_med else 0.0,
                "salt_matched": salt_matched,
                "attempts_count": len(res.attempts),
                "total_ms": total_ms,
            }
        )

    return {
        "recoverable_total": recoverable_total,
        "recoverable_passed": recoverable_passed,
        "recoverable_accuracy_pct": round(100.0 * recoverable_passed / recoverable_total, 1),
        "regional_total": regional_total,
        "regional_passed": regional_passed,
        "defect_total": defect_total,
        "defect_rejected_correctly": defect_rejected_correctly,
        "defect_rejection_accuracy_pct": round(100.0 * defect_rejected_correctly / defect_total, 1),
        "cases": rows,
    }


def run_day5_meal_and_e2e_usability_checks() -> dict:
    """Test meal quality gate, mandatory confirmation, edits, and Member 2 rule compatibility."""
    pipeline = AaharSmartScanPipeline(meal_vision=MealVisionService(api_key=""))
    consent = create_scan_consent(True)
    rules = load_member2_verified_rules(DATA_DIR / "verified_rules.json")

    scenarios = []

    s1_strip = pipeline.scan_medicine_strip(generate_strip_image_bytes("01_thyronorm_clean"), consent)
    s1_meal = pipeline.scan_meal_photo(
        generate_meal_image_bytes("morning_chai_with_milk"),
        consent,
        meal_slot="early_morning_empty_stomach",
        meal_hint="masala chai with milk",
    )
    pipeline.confirm_meal(
        s1_meal.session_id,
        MealConfirmationUpdate(confirm_food_ids=["chai_with_milk"], scheduled_time_hhmm="07:15"),
    )
    bundle1 = pipeline.export_handoff_bundle(consent, s1_meal.session_id, s1_strip.resolved_medications, preferred_language="hi")
    matches1 = check_member2_rule_compatibility(bundle1, rules)
    scenarios.append(
        {
            "scenario": "Thyroid + Morning Chai with Milk",
            "resolved_salts": bundle1.member2_lookup_keys.salt_names,
            "nutrients_flagged": bundle1.member2_lookup_keys.nutrient_flags,
            "matched_member2_rules": matches1,
        }
    )

    s2_strip = pipeline.scan_medicine_strip(generate_strip_image_bytes("06_warf_rotated_90"), consent)
    s2_meal = pipeline.scan_meal_photo(
        generate_meal_image_bytes("thali_palak_dal_curd"),
        consent,
        meal_slot="lunch",
    )
    pipeline.confirm_meal(
        s2_meal.session_id,
        MealConfirmationUpdate(
            confirm_food_ids=["palak_spinach", "dal_lentils", "curd_dahi"],
            scheduled_time_hhmm="13:00",
        ),
    )
    bundle2 = pipeline.export_handoff_bundle(consent, s2_meal.session_id, s2_strip.resolved_medications, preferred_language="hi")
    matches2 = check_member2_rule_compatibility(bundle2, rules)
    scenarios.append(
        {
            "scenario": "Warfarin (90deg rotated) + Indian Thali (Palak + Dal + Curd)",
            "resolved_salts": bundle2.member2_lookup_keys.salt_names,
            "nutrients_flagged": bundle2.member2_lookup_keys.nutrient_flags,
            "matched_member2_rules": matches2,
        }
    )

    s3_meal = pipeline.scan_meal_photo(
        generate_meal_image_bytes("meal_severe_blur"),
        consent,
        meal_slot="dinner",
    )
    scenarios.append(
        {
            "scenario": "Shaky / Blurred Meal Photo Retry",
            "retry_required": s3_meal.retry_required,
            "retry_guidance": s3_meal.quality_report.retry_guidance,
        }
    )

    return {"scenarios": scenarios}


def generate_pitch_visual_cards(strip_bench: dict) -> list[str]:
    """Generate ANVESHAN-anonymous Before/After pitch deck comparison PNG cards."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    f_title = _load_font(30)
    f_sub = _load_font(20)
    f_body = _load_font(17)

    showcase_cases = [
        ("03_shelcal_glare", "Glare Hotspot Strip -> Shelcal 500 -> Calcium Carbonate"),
        ("04_ciplox_low_contrast", "Low-Contrast Foil -> Ciplox 500 -> Ciprofloxacin"),
        ("12_ferro_xt_regional_glare", "Regional Glare Strip -> Ferro-XT -> Ferrous Ascorbate"),
    ]
    canvas = Image.new("RGB", (1360, 820), (246, 248, 247))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1360, 86), fill=(12, 107, 88))
    draw.text((34, 18), "Aahar-Rx Smart Scan: Before vs After OpenCV Foil Recovery", fill=(255, 255, 255), font=f_title)
    draw.text((34, 54), "Illumination Flattening + Specular Glare Inpainting + CLAHE + Fuzzy Salt Lookup", fill=(215, 244, 236), font=f_body)

    y = 108
    for cid, label in showcase_cases:
        bgr = decode_image_bytes(generate_strip_image_bytes(cid))
        variants, _ = enhance_strip_variants(bgr)
        enh = variants["enhanced_clahe"]

        raw_rgb = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).resize((460, 195))
        enh_rgb = Image.fromarray(cv2.cvtColor(enh, cv2.COLOR_BGR2RGB)).resize((460, 195))

        draw.text((36, y), label, fill=(20, 36, 30), font=f_sub)
        canvas.paste(raw_rgb, (36, y + 30))
        canvas.paste(enh_rgb, (536, y + 30))

        case_row = next(r for r in strip_bench["cases"] if r["case_id"] == cid)
        draw.rectangle((1020, y + 30, 1336, y + 225), fill=(255, 255, 255), outline=(12, 107, 88), width=2)
        draw.text((1038, y + 42), "Resolved Brand:", fill=(75, 93, 86), font=f_body)
        draw.text((1038, y + 66), str(case_row["resolved_brand"]), fill=(12, 107, 88), font=f_sub)
        draw.text((1038, y + 100), "Active Salt:", fill=(75, 93, 86), font=f_body)
        salt_wrapped = textwrap.fill(", ".join(case_row["resolved_salts"]), width=24)
        draw.multiline_text((1038, y + 124), salt_wrapped, fill=(20, 36, 30), font=f_body, spacing=3)
        draw.text((1038, y + 190), f"Conf: {int(case_row['confidence'] * 100)}% | {case_row['total_ms']} ms", fill=(75, 93, 86), font=f_body)
        y += 238

    out1 = REPORTS_DIR / "before_after_strip_recovery.png"
    canvas.save(out1)

    card2 = Image.new("RGB", (1280, 620), (246, 248, 247))
    d2 = ImageDraw.Draw(card2)
    d2.rectangle((0, 0, 1280, 82), fill=(12, 107, 88))
    d2.text((32, 22), "Aahar-Rx Member 1 Smart Scan: Consent -> Scan -> Mandatory Confirmation", fill=(255, 255, 255), font=f_title)

    boxes = [
        ("1. DPDP Pre-Scan Gate", "Explicit user consent\nbefore image decode.\nZero raw image storage."),
        ("2. OpenCV Quality Gate", "Checks blur, foil glare,\nlow-light & contrast.\nActionable retry tips."),
        ("3. Strip OCR + Lookup", "RapidOCR PP-OCRv4 +\nfuzzy brand-to-salt +\nmanual search fallback."),
        ("4. Meal Vision + Confirm", "Gemini 2.5 Flash JSON.\nAI guesses blocked until\nuser confirms/edits."),
    ]
    x = 34
    for title, desc in boxes:
        d2.rounded_rectangle((x, 120, x + 285, 345), radius=14, fill=(255, 255, 255), outline=(12, 107, 88), width=3)
        d2.text((x + 18, 138), title, fill=(12, 107, 88), font=f_sub)
        d2.text((x + 18, 185), desc, fill=(20, 36, 30), font=f_body)
        x += 308

    thali_img = Image.fromarray(cv2.cvtColor(decode_image_bytes(generate_meal_image_bytes("thali_palak_dal_curd")), cv2.COLOR_BGR2RGB)).resize((310, 220))
    card2.paste(thali_img, (34, 375))
    d2.rounded_rectangle((370, 375, 1244, 595), radius=14, fill=(227, 244, 239), outline=(12, 107, 88), width=2)
    d2.text((394, 395), "Validated Member 2/4 Handoff Summary (Schema v1.0.0)", fill=(12, 107, 88), font=f_sub)
    d2.text(
        (394, 435),
        "- Confirmed Foods: Palak Spinach, Dal Lentils, Curd/Dahi (confirmed_by_user: true)\n"
        "- Nutrient Interferents Flagged: calcium, iron, oxalates, phytates, vitamin_k\n"
        "- Clinical Safety Rule: Timing & dietary guidance only (never alters prescribed dose)",
        fill=(20, 36, 30),
        font=f_body,
    )

    out2 = REPORTS_DIR / "meal_confirmation_flow_visual.png"
    card2.save(out2)
    return [str(out1), str(out2)]


def write_accuracy_report(day1: dict, day4: dict, day5: dict, visuals: list[str]) -> None:
    """Write structured JSON results and Day 6 Markdown Accuracy Benchmark Report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "safety_disclaimer": CLINICAL_SAFETY_DISCLAIMER,
        "day1_ocr_engine_comparison": day1,
        "day4_full_strip_benchmark": day4,
        "day5_meal_and_e2e_checks": day5,
        "generated_visual_assets": visuals,
    }
    (REPORTS_DIR / "benchmark_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    lines = [
        "# Aahar-Rx Smart Scan (Member 1) — Accuracy Benchmark Report",
        "",
        f"> Generated UTC: `{results['generated_at_utc']}`  ",
        f"> Safety Notice: {CLINICAL_SAFETY_DISCLAIMER}",
        "",
        "## 1. Day 1 OCR Engine Research Comparison (Raw vs OpenCV Preprocessed)",
        "",
        "| OCR Engine | Raw Strip Salt Accuracy | Enhanced (CLAHE + Illumination Flatten) Accuracy | Mean Raw Latency (ms) | Mean Enhanced Latency (ms) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for eng_name, st in day1["summary"].items():
        lines.append(
            f"| `{eng_name}` | {st['raw_salt_hits']}/{st['total_cases']} ({st['raw_accuracy_pct']}%) | "
            f"{st['enhanced_salt_hits']}/{st['total_cases']} ({st['enhanced_accuracy_pct']}%) | "
            f"{st['mean_raw_latency_ms']} | {st['mean_enhanced_latency_ms']} |"
        )
    if not day1["tesseract_installed_locally"]:
        lines.append("")
        lines.append(
            "*Note: `TesseractOcrEngine` is implemented and supported in code; local `tesseract.exe` binary was not installed on this machine, so live comparisons ran on `rapidocr_paddle_ppocr` (PaddleOCR PP-OCRv4 ONNX) and `windows_media_ocr`.*"
        )

    lines.extend(
        [
            "",
            "## 2. Day 4 End-to-End 17-Strip Smart Scan Benchmark",
            "",
            f"- **Recoverable Strip Salt Accuracy**: **{day4['recoverable_passed']}/{day4['recoverable_total']} ({day4['recoverable_accuracy_pct']}%)**",
            f"- **Regional Brand Recovery**: **{day4['regional_passed']}/{day4['regional_total']}**",
            f"- **Unreadable Photo Rejection (Retry Gate)**: **{day4['defect_rejected_correctly']}/{day4['defect_total']} ({day4['defect_rejection_accuracy_pct']}%)**",
            "",
            "| Case ID | Condition | Quality Gate | Resolved Brand | Resolved Salts | Conf | Latency (ms) |",
            "| --- | --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in day4["cases"]:
        q_status = "RETRY" if row["retry_required"] else "PASS"
        salts = ", ".join(row["resolved_salts"]) if row["resolved_salts"] else "-"
        lines.append(
            f"| `{row['case_id']}` | {row['condition']} | {q_status} | {row['resolved_brand'] or '-'} | {salts} | {row['confidence']} | {row['total_ms']} |"
        )

    lines.extend(
        [
            "",
            "## 3. Day 5 Meal Vision, Mandatory Confirmation & Member 2 Integration Checks",
            "",
        ]
    )
    for sc in day5["scenarios"]:
        lines.append(f"- **{sc['scenario']}**: `{json.dumps(sc)}`")

    lines.extend(
        [
            "",
            "## 4. Pitch Visual Assets Generated",
            "",
            "- `reports/before_after_strip_recovery.png`",
            "- `reports/meal_confirmation_flow_visual.png`",
        ]
    )

    (REPORTS_DIR / "smart_scan_accuracy_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    day1 = run_day1_engine_comparison()
    day4 = run_day4_full_strip_benchmark()
    day5 = run_day5_meal_and_e2e_usability_checks()
    visuals = generate_pitch_visual_cards(day4)
    write_accuracy_report(day1, day4, day5, visuals)
    print(
        json.dumps(
            {
                "day1_summary": {
                    k: {
                        "raw_pct": v["raw_accuracy_pct"],
                        "enhanced_pct": v["enhanced_accuracy_pct"],
                        "mean_enhanced_ms": v["mean_enhanced_latency_ms"],
                    }
                    for k, v in day1["summary"].items()
                },
                "day4_recoverable_accuracy_pct": day4["recoverable_accuracy_pct"],
                "day4_defect_rejection_accuracy_pct": day4["defect_rejection_accuracy_pct"],
                "visuals": visuals,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
