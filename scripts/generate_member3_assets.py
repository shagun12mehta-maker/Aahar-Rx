"""Build Member 3 (App, UX & Language) frontend datasets, PK curves, samples, and TTS audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
TESTS_DIR = ROOT / "tests"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from aahar_ux import (  # noqa: E402
    build_all_pharmacokinetic_profiles,
    build_ux_alert_voice_scripts,
    build_voice_scripts_for_rules,
    get_ui_translations,
    synthesize_voice_assets,
)
from fixtures.generate_test_assets import (  # noqa: E402
    generate_meal_image_bytes,
    generate_strip_image_bytes,
)


def generate_static_data_and_samples(frontend_dir: Path) -> dict[str, int]:
    """Export rules, brands, food taxonomy, PK curves, EN/HI/MR translations, and demo samples."""
    data_dir = frontend_dir / "data"
    samples_dir = frontend_dir / "samples"
    data_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    rules = json.loads((ROOT / "data" / "verified_rules.json").read_text(encoding="utf-8"))
    brands = json.loads((ROOT / "data" / "indian_brand_to_salt.json").read_text(encoding="utf-8"))
    foods = json.loads((ROOT / "data" / "indian_food_taxonomy.json").read_text(encoding="utf-8"))

    pk_profiles = build_all_pharmacokinetic_profiles(rules)
    translations = get_ui_translations()
    voice_scripts = build_voice_scripts_for_rules(rules)
    ux_alerts = build_ux_alert_voice_scripts()

    (data_dir / "i18n.json").write_text(
        json.dumps(translations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (data_dir / "pk_profiles.json").write_text(
        json.dumps(pk_profiles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (data_dir / "voice_scripts.json").write_text(
        json.dumps(voice_scripts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (data_dir / "ux_voice_alerts.json").write_text(
        json.dumps(ux_alerts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (data_dir / "rules_bundle.json").write_text(
        json.dumps(
            {
                "rules": rules,
                "brands": brands["entries"],
                "foods": foods["foods"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    sample_strips = [
        "01_thyronorm_clean",
        "03_shelcal_glare",
        "04_ciplox_low_contrast",
        "05_orofer_dark_foil",
        "06_warf_rotated_90",
        "14_amlong_low_light_recoverable",
        "15_fail_severe_blur",
    ]
    sample_meals = [
        "morning_chai_with_milk",
        "thali_palak_dal_curd",
        "meal_severe_blur",
    ]

    for cid in sample_strips:
        (samples_dir / f"{cid}.png").write_bytes(generate_strip_image_bytes(cid))
    for mcid in sample_meals:
        (samples_dir / f"{mcid}.png").write_bytes(generate_meal_image_bytes(mcid))

    return {
        "rules_exported": len(rules),
        "brands_exported": len(brands["entries"]),
        "foods_exported": len(foods["foods"]),
        "pk_profiles": len(pk_profiles),
        "voice_scripts": len(voice_scripts),
        "samples_generated": len(sample_strips) + len(sample_meals),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Aahar-Rx Member 3 PWA datasets & voice assets.")
    parser.add_argument("--skip-tts", action="store_true", help="Skip edge-tts MP3 synthesis.")
    parser.add_argument("--overwrite-tts", action="store_true", help="Regenerate existing MP3 clips.")
    args = parser.parse_args()

    frontend_dir = ROOT / "frontend"
    summary = generate_static_data_and_samples(frontend_dir)
    if not args.skip_tts:
        rules = json.loads((ROOT / "data" / "verified_rules.json").read_text(encoding="utf-8"))
        tts_out = synthesize_voice_assets(rules, output_root=frontend_dir, overwrite=args.overwrite_tts)
        summary["mp3_files"] = len(tts_out["audio_files"])
        summary["total_audio_kb"] = round(sum(f["bytes"] for f in tts_out["audio_files"]) / 1024.0, 1)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
