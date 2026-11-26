"""Deterministic realistic medicine strip & Indian meal test image generator."""

from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class StripFixtureSpec:
    """Metadata describing a benchmark medicine strip image."""

    case_id: str
    expected_brand: str
    expected_salt: str
    expected_drug_class: str
    condition: str
    should_pass_quality: bool
    is_regional: bool = False


STRIP_SPECS: list[StripFixtureSpec] = [
    StripFixtureSpec("01_thyronorm_clean", "Thyronorm", "Levothyroxine Sodium", "thyroid", "clean", True),
    StripFixtureSpec("02_glycomet_curved_foil", "Glycomet", "Metformin Hydrochloride", "diabetes", "curved_foil", True),
    StripFixtureSpec("03_shelcal_glare", "Shelcal", "Calcium Carbonate", "anaemia_supplement", "glare_hotspot", True),
    StripFixtureSpec("04_ciplox_low_contrast", "Ciplox", "Ciprofloxacin", "antibiotic", "low_contrast_foil", True),
    StripFixtureSpec("05_orofer_dark_foil", "Orofer XT", "Ferrous Ascorbate", "anaemia_supplement", "dark_metallic_foil", True),
    StripFixtureSpec("06_warf_rotated_90", "Warf", "Warfarin Sodium", "anticoagulant", "rotated_90", True),
    StripFixtureSpec("07_atorva_rotated_180", "Atorva", "Atorvastatin", "statin", "rotated_180", True),
    StripFixtureSpec("08_telma_clean", "Telma", "Telmisartan", "blood_pressure", "clean", True),
    StripFixtureSpec("09_pan40_curved", "Pan 40", "Pantoprazole Sodium", "gastric_ppi", "curved_foil", True),
    StripFixtureSpec("10_augmentin_clean", "Augmentin", "Amoxicillin", "antibiotic", "clean", True),
    StripFixtureSpec("11_thyroup_regional", "Thyroup", "Levothyroxine Sodium", "thyroid", "regional_brand_curved", True, is_regional=True),
    StripFixtureSpec("12_ferro_xt_regional_glare", "Ferro-XT", "Ferrous Ascorbate", "anaemia_supplement", "regional_glare", True, is_regional=True),
    StripFixtureSpec("13_lasix_generic_salt", "Furosemide", "Furosemide", "diuretic", "back_of_strip_salt", True),
    StripFixtureSpec("14_amlong_low_light_recoverable", "Amlong", "Amlodipine Besylate", "blood_pressure", "dim_stage_light", True),
    StripFixtureSpec("15_fail_severe_blur", "Thyronorm", "Levothyroxine Sodium", "thyroid", "severe_blur_reject", False),
    StripFixtureSpec("16_fail_severe_dark", "Glycomet", "Metformin Hydrochloride", "diabetes", "severe_dark_reject", False),
    StripFixtureSpec("17_fail_severe_glare", "Ciplox", "Ciprofloxacin", "antibiotic", "severe_glare_reject", False),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_base_strip(
    headline: str,
    subtitle: str,
    footer: str,
    bg_rgb: tuple[int, int, int] = (238, 240, 244),
    text_rgb: tuple[int, int, int] = (22, 26, 38),
    accent_rgb: tuple[int, int, int] = (28, 92, 168),
) -> np.ndarray:
    w, h = 920, 420
    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    pocket_color = tuple(max(0, c - 26) for c in bg_rgb)
    for x in range(85, w - 70, 175):
        draw.ellipse((x - 42, 16, x + 42, 74), outline=pocket_color, width=3)
        draw.ellipse((x - 42, h - 74, x + 42, h - 16), outline=pocket_color, width=3)

    draw.rectangle((45, 95, w - 45, 108), fill=accent_rgb)
    f_big = _load_font(60)
    f_med = _load_font(34)
    f_small = _load_font(24)

    draw.text((65, 130), headline, fill=text_rgb, font=f_big)
    draw.text((65, 220), subtitle, fill=text_rgb, font=f_med)
    draw.text((65, 285), footer, fill=accent_rgb, font=f_small)

    rgb = np.array(img, dtype=np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _apply_curved_foil_gradient(bgr: np.ndarray, strength: float = 0.42) -> np.ndarray:
    h, w = bgr.shape[:2]
    y = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    curve = 1.0 - strength * (y ** 2) + 0.14 * np.sin(np.linspace(0, np.pi * 2, w, dtype=np.float32))[None, :]
    shaded = bgr.astype(np.float32) * curve[:, :, None]
    return np.clip(shaded, 0, 255).astype(np.uint8)


def _apply_specular_glare(
    bgr: np.ndarray,
    center_xy: tuple[float, float] = (0.76, 0.48),
    radius_frac: float = 0.14,
    intensity: float = 250.0,
) -> np.ndarray:
    h, w = bgr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = center_xy[0] * w
    cy = center_xy[1] * h
    sigma = max(w, h) * radius_frac
    dist2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma * sigma)
    spot = np.exp(-dist2) * intensity
    out = bgr.astype(np.float32) + spot[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def generate_strip_image_bytes(case_id: str) -> bytes:
    """Render deterministic PNG bytes for a named benchmark medicine strip case."""
    if case_id == "01_thyronorm_clean":
        bgr = _render_base_strip("THYRONORM 50", "Levothyroxine Sodium IP 50 mcg", "Rx Thyroid Hormone Tablets")
    elif case_id == "02_glycomet_curved_foil":
        bgr = _render_base_strip("GLYCOMET 500 SR", "Metformin Hydrochloride IP 500 mg", "Sustained Release Foil Strip", bg_rgb=(205, 210, 218))
        bgr = _apply_curved_foil_gradient(bgr, strength=0.52)
    elif case_id == "03_shelcal_glare":
        bgr = _render_base_strip("SHELCAL 500", "Calcium Carbonate + Vitamin D3", "Film Coated Tablets", bg_rgb=(210, 216, 224))
        bgr = _apply_curved_foil_gradient(bgr, strength=0.35)
        bgr = _apply_specular_glare(bgr, center_xy=(0.82, 0.45), radius_frac=0.11, intensity=230.0)
    elif case_id == "04_ciplox_low_contrast":
        bgr = _render_base_strip("CIPLOX 500", "Ciprofloxacin IP 500 mg", "Antibiotic Tablets", bg_rgb=(178, 184, 192), text_rgb=(108, 114, 126), accent_rgb=(95, 108, 130))
        bgr = _apply_curved_foil_gradient(bgr, strength=0.30)
    elif case_id == "05_orofer_dark_foil":
        bgr = _render_base_strip("OROFER XT", "Ferrous Ascorbate 100 mg + Folic Acid", "Iron Supplement Strip", bg_rgb=(96, 26, 36), text_rgb=(245, 240, 232), accent_rgb=(235, 190, 95))
    elif case_id == "06_warf_rotated_90":
        bgr = _render_base_strip("WARF 5", "Warfarin Sodium IP 5 mg", "Anticoagulant Tablets")
        bgr = cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    elif case_id == "07_atorva_rotated_180":
        bgr = _render_base_strip("ATORVA 20", "Atorvastatin Calcium IP 20 mg", "Lipid Lowering Strip")
        bgr = cv2.rotate(bgr, cv2.ROTATE_180)
    elif case_id == "08_telma_clean":
        bgr = _render_base_strip("TELMA 40", "Telmisartan IP 40 mg", "Antihypertensive Tablets")
    elif case_id == "09_pan40_curved":
        bgr = _render_base_strip("PAN 40", "Pantoprazole Sodium IP 40 mg", "Gastro-Resistant Strip", bg_rgb=(215, 220, 226))
        bgr = _apply_curved_foil_gradient(bgr, strength=0.48)
    elif case_id == "10_augmentin_clean":
        bgr = _render_base_strip("AUGMENTIN 625 DUO", "Amoxicillin 500 mg + Clavulanic Acid 125 mg", "Antibiotic Tablets")
    elif case_id == "11_thyroup_regional":
        bgr = _render_base_strip("THYROUP 50", "Levothyroxine Sodium 50 mcg", "Regional Generic Strip", bg_rgb=(208, 215, 222))
        bgr = _apply_curved_foil_gradient(bgr, strength=0.40)
    elif case_id == "12_ferro_xt_regional_glare":
        bgr = _render_base_strip("FERRO-XT", "Ferrous Ascorbate + Folic Acid", "Haematinic Tablets", bg_rgb=(200, 206, 214))
        bgr = _apply_specular_glare(bgr, center_xy=(0.80, 0.55), radius_frac=0.10, intensity=210.0)
    elif case_id == "13_lasix_generic_salt":
        bgr = _render_base_strip("FUROSEMIDE 40 MG", "Each uncoated tablet contains Furosemide IP 40 mg", "Generic Composition Back")
    elif case_id == "14_amlong_low_light_recoverable":
        bgr = _render_base_strip("AMLONG 5", "Amlodipine Besilate IP 5 mg", "Calcium Channel Blocker")
        bgr = np.clip(bgr.astype(np.float32) * 0.34, 0, 255).astype(np.uint8)
    elif case_id == "15_fail_severe_blur":
        bgr = _render_base_strip("THYRONORM 50", "Levothyroxine Sodium IP 50 mcg", "Blurred Strip")
        bgr = cv2.GaussianBlur(bgr, (29, 29), sigmaX=12.0)
    elif case_id == "16_fail_severe_dark":
        bgr = _render_base_strip("GLYCOMET 500", "Metformin Hydrochloride 500 mg", "Dark Strip")
        bgr = np.clip(bgr.astype(np.float32) * 0.09, 0, 255).astype(np.uint8)
    elif case_id == "17_fail_severe_glare":
        bgr = _render_base_strip("CIPLOX 500", "Ciprofloxacin 500 mg", "Blown Out Glare", bg_rgb=(190, 195, 202))
        bgr = _apply_specular_glare(bgr, center_xy=(0.45, 0.48), radius_frac=0.32, intensity=255.0)
    else:
        raise KeyError(f"Unknown strip test case: {case_id}")

    ok, encoded = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError(f"Failed to encode fixture: {case_id}")
    return encoded.tobytes()


def generate_meal_image_bytes(meal_case: str) -> bytes:
    """Render deterministic PNG bytes for Indian meal vision test cases."""
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (235, 228, 214))
    draw = ImageDraw.Draw(img)

    if meal_case == "thali_palak_dal_curd":
        draw.ellipse((80, 40, 720, 560), fill=(195, 202, 210), outline=(120, 130, 140), width=6)
        draw.ellipse((150, 95, 340, 275), fill=(36, 128, 52), outline=(90, 95, 105), width=5)
        draw.ellipse((370, 90, 560, 270), fill=(224, 174, 38), outline=(90, 95, 105), width=5)
        draw.ellipse((510, 250, 675, 415), fill=(244, 242, 236), outline=(90, 95, 105), width=5)
        draw.ellipse((175, 300, 445, 520), fill=(198, 152, 92), outline=(145, 104, 52), width=4)
    elif meal_case == "morning_chai_with_milk":
        draw.ellipse((170, 100, 630, 520), fill=(238, 236, 232), outline=(165, 165, 175), width=5)
        draw.ellipse((245, 165, 555, 455), fill=(164, 114, 72), outline=(250, 248, 244), width=12)
    elif meal_case == "meal_severe_blur":
        draw.ellipse((170, 100, 630, 520), fill=(210, 170, 90), outline=(120, 90, 50), width=5)
        bgr = cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        bgr = cv2.GaussianBlur(bgr, (37, 37), sigmaX=15.0)
        _, enc = cv2.imencode(".png", bgr)
        return enc.tobytes()
    elif meal_case == "meal_severe_dark":
        draw.ellipse((170, 100, 630, 520), fill=(210, 170, 90), outline=(120, 90, 50), width=5)
        bgr = cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        bgr = np.clip(bgr.astype(np.float32) * 0.08, 0, 255).astype(np.uint8)
        _, enc = cv2.imencode(".png", bgr)
        return enc.tobytes()
    else:
        raise KeyError(f"Unknown meal test case: {meal_case}")

    bgr = cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
    _, encoded = cv2.imencode(".png", bgr)
    return encoded.tobytes()
