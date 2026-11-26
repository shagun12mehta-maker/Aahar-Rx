"""Day 7 Member 3 live demo rehearsal verification (Absorption Curve, Voice EN/HI/MR, QR Pass)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aahar_ux import (  # noqa: E402
    build_all_pharmacokinetic_profiles,
    build_voice_scripts_for_rules,
    validate_translation_bundle,
)


def main() -> None:
    frontend = ROOT / "frontend"
    rules = json.loads((ROOT / "data" / "verified_rules.json").read_text(encoding="utf-8"))
    i18n = json.loads((frontend / "data" / "i18n.json").read_text(encoding="utf-8"))
    profiles = build_all_pharmacokinetic_profiles(rules)
    scripts = build_voice_scripts_for_rules(rules)

    print("=== [1/4] Trilingual Localization (EN / HI / MR) ===")
    assert validate_translation_bundle(i18n) == []
    print("Languages verified:", ", ".join(i18n[k]["meta"]["native_label"] for k in ("en", "hi", "mr")))

    print("\n=== [2/4] Pharmacokinetic Absorption Curve Metrics ===")
    thy = profiles["RULE-THY-001"]
    amp = profiles["RULE-HTN-005"]
    print(f"Levothyroxine peak drop: {thy['interfered_peak_pct']}% (Tmax {thy['baseline_tmax_hours']}h -> {thy['interfered_tmax_hours']}h)")
    print(f"Amlodipine CYP3A4 elevation: {amp['interfered_peak_pct']}% (above {amp['safety_ceiling_pct']}% safety limit)")

    print("\n=== [3/4] Elderly Voice Reminders (EN / HI / MR Audio) ===")
    for lang in ("en", "hi", "mr"):
        clip = frontend / scripts["RULE-THY-001"]["languages"][lang]["audio_rel_path"]
        assert clip.exists()
        print(f"{lang.upper()} audio ready: {clip.name} ({clip.stat().st_size} bytes)")

    print("\n=== [4/4] Offline PWA & 1-Click QR Pass Readiness ===")
    for fname in ("index.html", "manifest.webmanifest", "sw.js", "vendor/qrcode.min.js", "vendor/chart.umd.min.js"):
        assert (frontend / fname).exists()
    print("PWA static assets + ISO QR + Chart.js 4 ready at http://127.0.0.1:8030/")


if __name__ == "__main__":
    main()
