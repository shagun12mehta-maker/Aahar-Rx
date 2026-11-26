"""Generate ANVESHAN-anonymous pitch deck visual cards from live backend calculations."""

from __future__ import annotations

from pathlib import Path
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aahar_backend.conflict_engine import build_pharmacokinetic_curve  # noqa: E402
from aahar_backend.db import AaharDatabase  # noqa: E402
from aahar_backend.models import (  # noqa: E402
    ConsentCreateRequest,
    MealSlotInput,
    MedicationDoseInput,
    UserCreateRequest,
)
from aahar_backend.timetable_engine import generate_safe_timetable  # noqa: E402

REPORTS_DIR = PROJECT_ROOT / "reports"


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_system_architecture_card() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1320, 740), (246, 248, 247))
    draw = ImageDraw.Draw(img)
    f_title = _load_font(30)
    f_sub = _load_font(20)
    f_body = _load_font(17)

    draw.rectangle((0, 0, 1320, 92), fill=(12, 107, 88))
    draw.text((34, 18), "Aahar-Rx System Architecture & DPDP Act 2023 Safety Gate", fill=(255, 255, 255), font=f_title)
    draw.text((34, 56), "FastAPI Backend • Supabase/PostgreSQL Schema • Deterministic Clinical Rules • Blind-Review Safe", fill=(215, 244, 236), font=f_body)

    boxes = [
        ("Member 1: Smart Scan", "Strip OCR & Meal Vision.\nMandatory user confirm.\nSends salts + foods ONLY."),
        ("DPDP Privacy Gate", "Explicit DB consent logged\nbefore any processing.\nZero raw images stored."),
        ("Member 4: FastAPI Core", "/check-conflict &\n/generate-timetable APIs.\nSafe gaps + PK curves."),
        ("Member 2: Clinical Data", "verified_rules.json\nICMR-NIN IFCT 2017 &\nOpenFDA doctor-signed."),
    ]
    x = 34
    for title, body in boxes:
        draw.rounded_rectangle((x, 128, x + 295, 345), radius=14, fill=(255, 255, 255), outline=(12, 107, 88), width=3)
        draw.text((x + 18, 148), title, fill=(12, 107, 88), font=f_sub)
        draw.multiline_text((x + 18, 194), body, fill=(20, 36, 30), font=f_body, spacing=6)
        x += 318

    # Relational Schema + Right to Erasure card
    draw.rounded_rectangle((34, 380, 650, 700), radius=14, fill=(255, 255, 255), outline=(12, 107, 88), width=2)
    draw.text((56, 400), "PostgreSQL / Supabase Schema v1", fill=(12, 107, 88), font=f_sub)
    schema_txt = (
        "- users: pseudonymous usr_* IDs, language (en/hi/mr)\n"
        "- consent_logs: DPDP audit ledger, raw_images_stored=FALSE\n"
        "- salts & foods: normalized active salts & IFCT 2017 codes\n"
        "- rules: 8 verified clinical rules (gaps, PK drops, swaps)\n"
        "- scan_records & schedules: confirmed metadata + QR Health Pass"
    )
    draw.multiline_text((56, 444), schema_txt, fill=(20, 36, 30), font=f_body, spacing=10)

    draw.rounded_rectangle((675, 380, 1286, 700), radius=14, fill=(227, 244, 239), outline=(12, 107, 88), width=2)
    draw.text((697, 400), "DPDP Act 2023 & Clinical Guardrails", fill=(12, 107, 88), font=f_sub)
    guard_txt = (
        "- Missing/withdrawn consent -> HTTP 403 Forbidden\n"
        "- Raw image/base64 payloads -> HTTP 422 Rejected\n"
        "- Right to Erasure -> DELETE /api/v1/users/{id}/data\n"
        "- Clinical Safety Boundary -> Timing & kitchen swaps only;\n"
        "  never advises skipping, altering, or replacing doses."
    )
    draw.multiline_text((697, 444), guard_txt, fill=(20, 36, 30), font=f_body, spacing=10)

    out = REPORTS_DIR / "system_architecture_and_dpdp.png"
    img.save(out)
    return out


def render_absorption_and_timetable_card() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    db = AaharDatabase(db_path=":memory:")
    rules = db.list_rules()
    user = db.create_user(UserCreateRequest(preferred_language="en"))
    consent = db.record_consent(ConsentCreateRequest(user_id=user.user_id, consented=True))

    # Real PK curve for Iron + Chai (62% drop, +2.0h Tmax delay)
    curve = build_pharmacokinetic_curve(bioavailability_drop_pct=62.0, t_max_delay_hours=2.0)

    # Real multi-drug timetable
    tt = generate_safe_timetable(
        user_id=user.user_id,
        consent_id=consent.consent_id,
        medications=[
            MedicationDoseInput(medicine_label="Thyronorm", active_salt="Levothyroxine Sodium", preferred_time_hhmm="06:30"),
            MedicationDoseInput(medicine_label="Orofer XT", active_salt="Ferrous Ascorbate", preferred_time_hhmm="13:15"),
        ],
        meals=[
            MealSlotInput(meal_slot="early_morning_empty_stomach", time_hhmm="07:00", food_items=["Morning Masala Chai with Milk"]),
            MealSlotInput(meal_slot="lunch", time_hhmm="13:00", food_items=["Palak Paneer", "Masala Chai"]),
        ],
        rules=rules,
    )

    img = Image.new("RGB", (1340, 740), (246, 248, 247))
    draw = ImageDraw.Draw(img)
    f_title = _load_font(28)
    f_sub = _load_font(20)
    f_body = _load_font(16)

    draw.rectangle((0, 0, 1340, 88), fill=(12, 107, 88))
    draw.text((34, 16), "Aahar-Rx Backend Output: Pharmacokinetic Curve & Safe Time-Gap Timetable", fill=(255, 255, 255), font=f_title)
    draw.text((34, 52), "Generated directly from Member 2 verified_rules.json via /check-conflict and /generate-timetable", fill=(215, 244, 236), font=f_body)

    # Left panel: Absorption curve plot
    px0, py0, px1, py1 = 44, 125, 650, 680
    draw.rounded_rectangle((px0, py0, px1, py1), radius=14, fill=(255, 255, 255), outline=(12, 107, 88), width=2)
    draw.text((px0 + 22, py0 + 18), "Iron Absorption: Normal vs. With Masala Chai (-62%)", fill=(12, 107, 88), font=f_sub)

    gx0, gy0, gx1, gy1 = px0 + 62, py0 + 80, px1 - 36, py1 - 85
    draw.line((gx0, gy1, gx1, gy1), fill=(40, 50, 46), width=2)
    draw.line((gx0, gy0, gx0, gy1), fill=(40, 50, 46), width=2)

    def _pt(t_hr: float, pct: float) -> tuple[int, int]:
        x = gx0 + int((t_hr / 8.0) * (gx1 - gx0))
        y = gy1 - int((min(pct, 110.0) / 110.0) * (gy1 - gy0))
        return x, y

    norm_pts = [_pt(p.time_hours, p.normal_efficacy_pct) for p in curve]
    int_pts = [_pt(p.time_hours, p.interfered_efficacy_pct) for p in curve]
    draw.line(norm_pts, fill=(12, 107, 88), width=4)
    draw.line(int_pts, fill=(210, 48, 48), width=4)

    for tick in (0, 2, 4, 6, 8):
        tx, ty = _pt(float(tick), 0.0)
        draw.line((tx, ty, tx, ty + 6), fill=(40, 50, 46), width=2)
        draw.text((tx - 8, ty + 12), f"{tick}h", fill=(60, 72, 68), font=f_body)
    draw.text((gx1 - 60, gy1 + 36), "Time (h)", fill=(60, 72, 68), font=f_body)
    draw.rectangle((gx0 + 220, py0 + 68, gx0 + 510, py0 + 122), fill=(246, 248, 247), outline=(200, 210, 206), width=1)
    draw.line((gx0 + 235, py0 + 84, gx0 + 270, py0 + 84), fill=(12, 107, 88), width=4)
    draw.text((gx0 + 280, py0 + 75), "Normal Uptake (100%)", fill=(20, 36, 30), font=f_body)
    draw.line((gx0 + 235, py0 + 106, gx0 + 270, py0 + 106), fill=(210, 48, 48), width=4)
    draw.text((gx0 + 280, py0 + 97), "With Chai (-62%, +2h Tmax)", fill=(180, 35, 35), font=f_body)

    # Right panel: Generated Timetable
    tx0, ty0, tx1, ty1 = 678, 125, 1300, 680
    draw.rounded_rectangle((tx0, ty0, tx1, ty1), radius=14, fill=(255, 255, 255), outline=(12, 107, 88), width=2)
    draw.text((tx0 + 22, ty0 + 18), "Generated Safe Time-Gap Schedule", fill=(12, 107, 88), font=f_sub)

    y = ty0 + 66
    for entry in tt.timeline:
        is_shifted = entry.status != "safe_as_planned"
        bg = (255, 247, 232) if is_shifted else (235, 247, 243)
        border = (217, 119, 6) if is_shifted else (12, 107, 88)
        draw.rounded_rectangle((tx0 + 22, y, tx1 - 22, y + 104), radius=10, fill=bg, outline=border, width=2)
        pretty_label = entry.label.replace("early_morning_empty_stomach", "Morning")
        if len(pretty_label) > 46:
            pretty_label = pretty_label[:43] + "..."
        draw.text((tx0 + 36, y + 10), f"{entry.recommended_time_hhmm}  |  {pretty_label}", fill=(20, 36, 30), font=f_sub)
        wrapped = textwrap.fill(entry.guidance, width=62)
        draw.multiline_text((tx0 + 36, y + 40), wrapped, fill=(55, 68, 63), font=f_body, spacing=2)
        y += 116

    out = REPORTS_DIR / "absorption_curve_and_timetable.png"
    img.save(out)
    return out


def main() -> None:
    p1 = render_system_architecture_card()
    p2 = render_absorption_and_timetable_card()
    print(f"Generated pitch visuals:\n- {p1}\n- {p2}")


if __name__ == "__main__":
    main()
