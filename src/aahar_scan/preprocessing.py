"""OpenCV image quality inspection, retry guidance, and curved-foil/glare enhancement."""

from __future__ import annotations

from typing import Literal

import cv2
import numpy as np

from .models import ImageQualityReport


def decode_image_bytes(image_bytes: bytes, max_edge: int = 1600, min_edge: int = 480) -> np.ndarray:
    """Decode raw image bytes into a normalized BGR ndarray (in-memory only)."""
    if not image_bytes:
        raise ValueError("Empty image payload received.")
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None or bgr.size == 0:
        raise ValueError("Unable to decode image bytes; ensure valid PNG, JPEG, or WEBP input.")

    h, w = bgr.shape[:2]
    longest = max(h, w)
    if longest > max_edge:
        scale = max_edge / float(longest)
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    elif longest < min_edge:
        scale = min_edge / float(longest)
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    return bgr


def _resize_for_metrics(bgr: np.ndarray, target_width: int = 800) -> np.ndarray:
    h, w = bgr.shape[:2]
    if w == target_width:
        return bgr
    scale = target_width / float(w)
    new_h = max(64, int(h * scale))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(bgr, (target_width, new_h), interpolation=interp)


def _estimate_skew_deg(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 60, 180)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=60,
        minLineLength=max(40, gray.shape[1] // 8),
        maxLineGap=15,
    )
    if lines is None or len(lines) == 0:
        return 0.0
    angles: list[float] = []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4)[:40]:
        dx = int(x2) - int(x1)
        dy = int(y2) - int(y1)
        if abs(dx) < 1e-3 and abs(dy) < 1e-3:
            continue
        angle = float(np.degrees(np.arctan2(dy, dx)))
        while angle > 45.0:
            angle -= 90.0
        while angle < -45.0:
            angle += 90.0
        angles.append(angle)
    if not angles:
        return 0.0
    return round(float(np.median(angles)), 2)


def _detect_specular_glare(hsv: np.ndarray, gray: np.ndarray) -> float:
    """Measure specular glare hotspot ratio (clipped bright low-gradient patches)."""
    s_chan = hsv[:, :, 1]
    v_chan = hsv[:, :, 2]
    bright_neutral = (v_chan >= 252) & (s_chan <= 20)

    bright_frac = float(np.mean(bright_neutral))
    if bright_frac > 0.55 and float(np.std(gray)) >= 22.0:
        strict_clip = (v_chan >= 254) & (s_chan <= 15)
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(grad_x, grad_y)
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(strict_clip.astype(np.uint8))
        total_px = gray.shape[0] * gray.shape[1]
        blob_px = sum(
            int(stats[i, cv2.CC_STAT_AREA])
            for i in range(1, num_labels)
            if stats[i, cv2.CC_STAT_AREA] >= total_px * 0.015
            and float(np.mean(grad_mag[strict_clip])) < 25.0
        )
        return round(blob_px / float(total_px), 4)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned_mask = cv2.morphologyEx(bright_neutral.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    return round(float(np.mean(cleaned_mask > 0)), 4)


def inspect_image_quality(
    bgr: np.ndarray,
    mode: Literal["strip", "meal"] = "strip",
) -> ImageQualityReport:
    """Check blur, specular glare, brightness, and contrast with elderly-friendly retry tips."""
    norm = _resize_for_metrics(bgr, target_width=800)
    gray = cv2.cvtColor(norm, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(norm, cv2.COLOR_BGR2HSV)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(np.mean(hsv[:, :, 2]))
    contrast_std = float(np.std(gray))
    glare_ratio = _detect_specular_glare(hsv, gray)
    skew_deg = _estimate_skew_deg(gray)

    issues: list[str] = []
    guidance: list[str] = []

    blur_threshold = 42.0 if mode == "strip" else 28.0
    if blur_score < blur_threshold:
        issues.append("motion_or_focus_blur")
        guidance.append(
            "Photo looks blurry. Hold the camera steady 15-20 cm away and tap the screen to focus before capturing."
        )

    glare_threshold = 0.25 if mode == "strip" else 0.28
    if glare_ratio > glare_threshold:
        issues.append("specular_glare")
        guidance.append(
            "Bright glare detected on the surface. Tilt slightly away from overhead light or turn off camera flash."
        )

    if mean_brightness < 48.0:
        issues.append("low_light")
        guidance.append(
            "Photo is too dark. Move closer to a window or room light and retake."
        )
    elif mean_brightness > 246.0:
        issues.append("overexposed")
        guidance.append(
            "Photo is overly bright/washed out. Reduce direct light and retake."
        )

    contrast_threshold = 18.0 if mode == "strip" else 16.0
    if contrast_std < contrast_threshold:
        issues.append("low_contrast")
        guidance.append(
            "Text or dish edges have very low contrast. Place on a plain darker or contrasting surface and retake."
        )

    severe_blur = blur_score < (blur_threshold * 0.68)
    severe_dark = mean_brightness < 38.0
    severe_glare = (glare_ratio > (0.36 if mode == "strip" else 0.40)) or (
        glare_ratio > 0.24 and contrast_std < 28.0
    )
    severe_contrast = contrast_std < 12.0

    passed = not (severe_blur or severe_dark or severe_glare or severe_contrast or len(issues) >= 2)

    blur_norm = min(1.0, blur_score / 180.0)
    contrast_norm = min(1.0, contrast_std / 55.0)
    glare_penalty = min(1.0, glare_ratio * 3.0)
    brightness_penalty = 0.0
    if mean_brightness < 55.0:
        brightness_penalty = (55.0 - mean_brightness) / 55.0
    elif mean_brightness > 235.0:
        brightness_penalty = (mean_brightness - 235.0) / 25.0

    quality_score = max(
        0.0,
        min(
            1.0,
            0.45 * blur_norm + 0.35 * contrast_norm + 0.20 * (1.0 - glare_penalty) - 0.3 * brightness_penalty,
        ),
    )

    return ImageQualityReport(
        passed=passed,
        quality_score=round(quality_score, 3),
        blur_score=round(blur_score, 2),
        glare_ratio=glare_ratio,
        mean_brightness=round(mean_brightness, 2),
        contrast_std=round(contrast_std, 2),
        estimated_skew_deg=skew_deg,
        issues=issues,
        retry_guidance=guidance,
        preprocessing_applied=[],
    )


def suppress_foil_glare(bgr: np.ndarray) -> np.ndarray:
    """Suppress specular foil glare spots via gentle highlight rolloff / small-speck inpaint."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 2] >= 252) & (hsv[:, :, 1] <= 20)).astype(np.uint8) * 255
    frac = float(np.mean(mask > 0))
    if 0.002 < frac < 0.05:
        dilated = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
        return cv2.inpaint(bgr, dilated, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    if 0.05 <= frac < 0.28:
        soft_mask = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), sigmaX=7)
        attenuated = bgr.astype(np.float32) * (1.0 - 0.22 * soft_mask[:, :, None])
        return np.clip(attenuated, 0, 255).astype(np.uint8)
    return bgr


def flatten_curved_illumination(gray: np.ndarray) -> np.ndarray:
    """Divide out smooth curved-foil lighting gradients using morphological background estimation."""
    kernel_size = max(31, (min(gray.shape[:2]) // 8) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    background = cv2.GaussianBlur(background, (0, 0), sigmaX=9, sigmaY=9)
    background = np.maximum(background, 1)
    flattened = cv2.divide(gray.astype(np.float32), background.astype(np.float32), scale=235.0)
    return np.clip(flattened, 0, 255).astype(np.uint8)


def enhance_strip_variants(bgr: np.ndarray) -> tuple[dict[str, np.ndarray], list[str]]:
    """Build enhanced image variants to recover curved, glare-affected, or low-contrast strips."""
    applied_steps: list[str] = []

    deglared = suppress_foil_glare(bgr)
    if not np.array_equal(deglared, bgr):
        applied_steps.append("specular_glare_inpaint")

    lab = cv2.cvtColor(deglared, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    flat_l = flatten_curved_illumination(l_chan)
    p5, p95 = np.percentile(flat_l, (5, 95))
    if p95 - p5 < 140:
        flat_l = cv2.normalize(flat_l, None, 12, 248, cv2.NORM_MINMAX)
    applied_steps.append("curved_foil_illumination_flatten")

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    clahe_l = clahe.apply(flat_l)
    applied_steps.append("clahe_contrast_boost")

    merged_lab = cv2.merge((clahe_l, a_chan, b_chan))
    enhanced_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
    blurred = cv2.GaussianBlur(enhanced_bgr, (0, 0), sigmaX=1.4)
    sharpened_bgr = cv2.addWeighted(enhanced_bgr, 1.55, blurred, -0.55, 0)
    applied_steps.append("unsharp_text_sharpening")

    gray = cv2.cvtColor(deglared, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=35, sigmaSpace=35)
    flat_gray = flatten_curved_illumination(denoised)
    clahe_gray = clahe.apply(flat_gray)
    clahe_gray_bgr = cv2.cvtColor(clahe_gray, cv2.COLOR_GRAY2BGR)

    inverted_bgr = cv2.bitwise_not(clahe_gray_bgr)
    applied_steps.append("foil_polarity_normalization")

    return (
        {
            "enhanced_clahe": sharpened_bgr,
            "illumination_flat_gray": clahe_gray_bgr,
            "inverted_foil": inverted_bgr,
        },
        applied_steps,
    )


def rotate_image(bgr: np.ndarray, angle_deg: int) -> np.ndarray:
    """Rotate image cleanly by 90/180/270 degrees for sideways strip recovery."""
    angle = angle_deg % 360
    if angle == 0:
        return bgr
    if angle == 90:
        return cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(bgr, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Unsupported right-angle rotation: {angle_deg}")
