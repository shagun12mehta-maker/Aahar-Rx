"""Multi-engine medicine strip OCR backends and smart glare/rotation recovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
import base64
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Sequence

import cv2
import numpy as np

from .models import OcrEngineAttempt, ResolvedMedication, StripScanResult
from .preprocessing import (
    decode_image_bytes,
    enhance_strip_variants,
    inspect_image_quality,
    rotate_image,
)
from .salt_resolver import SaltResolver


class BaseOcrEngine(ABC):
    """Abstract interface for medicine strip OCR backends."""

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this OCR backend is usable in the current environment."""

    @abstractmethod
    def recognize(self, bgr: np.ndarray, variant_name: str = "raw") -> OcrEngineAttempt:
        """Run OCR on an in-memory BGR image array."""


class RapidOcrEngine(BaseOcrEngine):
    """PaddleOCR PP-OCRv4 ONNX engine running 100% in-memory via rapidocr-onnxruntime."""

    name = "rapidocr_paddle_ppocr"
    _shared_instance = None

    def is_available(self) -> bool:
        try:
            import rapidocr_onnxruntime  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def _get_ocr(cls):
        if cls._shared_instance is None:
            from rapidocr_onnxruntime import RapidOCR

            cls._shared_instance = RapidOCR()
        return cls._shared_instance

    def recognize(self, bgr: np.ndarray, variant_name: str = "raw") -> OcrEngineAttempt:
        start = time.perf_counter()
        ocr = self._get_ocr()
        result, _ = ocr(bgr)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        lines: list[str] = []
        confs: list[float] = []
        if result:
            for item in result:
                if len(item) >= 3:
                    text = str(item[1]).strip()
                    conf = float(item[2])
                    if text:
                        lines.append(text)
                        confs.append(max(0.0, min(1.0, conf)))

        mean_conf = sum(confs) / len(confs) if confs else 0.0
        return OcrEngineAttempt(
            engine_name=self.name,
            variant_name=variant_name,
            raw_text=" | ".join(lines),
            lines=lines,
            mean_confidence=round(mean_conf, 3),
            latency_ms=round(elapsed_ms, 2),
        )


class WindowsNativeOcrEngine(BaseOcrEngine):
    """Windows 10/11 built-in WinRT OCR engine for Day 1 comparative benchmarking."""

    name = "windows_media_ocr"

    def is_available(self) -> bool:
        return os.name == "nt" and shutil.which("powershell") is not None

    def recognize(self, bgr: np.ndarray, variant_name: str = "raw") -> OcrEngineAttempt:
        start = time.perf_counter()
        if not self.is_available():
            return OcrEngineAttempt(
                engine_name=self.name,
                variant_name=variant_name,
                raw_text="",
                lines=[],
                mean_confidence=0.0,
                latency_ms=0.0,
            )

        ok, encoded = cv2.imencode(".png", bgr)
        if not ok:
            raise ValueError("Failed to encode image buffer for Windows OCR.")

        b64_png = base64.b64encode(encoded.tobytes()).decode("ascii")
        lines: list[str] = []
        ps_script = (
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
            "[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null; "
            "[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null; "
            "$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { "
            "$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]; "
            "Function Await($WinRtTask, $ResultType) { "
            "$netTask = $asTaskGeneric.MakeGenericMethod($ResultType).Invoke($null, @($WinRtTask)); "
            "$netTask.Wait(-1) | Out-Null; $netTask.Result }; "
            f"$bytes = [System.Convert]::FromBase64String('{b64_png}'); "
            "$ms = New-Object System.IO.MemoryStream(,$bytes); "
            "$ras = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($ms); "
            "$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($ras)) ([Windows.Graphics.Imaging.BitmapDecoder]); "
            "$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]); "
            "if ($bitmap.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8) { "
            "$bitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert($bitmap, [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied) }; "
            "$ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
            "if ($null -ne $ocr) { "
            "$res = Await ($ocr.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult]); "
            "$res.Lines | ForEach-Object { $_.Text } }; "
            "$ras.Dispose(); $ms.Dispose()"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "-"],
            input=ps_script,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return OcrEngineAttempt(
            engine_name=self.name,
            variant_name=variant_name,
            raw_text=" | ".join(lines),
            lines=lines,
            mean_confidence=0.75 if lines else 0.0,
            latency_ms=round(elapsed_ms, 2),
        )


class TesseractOcrEngine(BaseOcrEngine):
    """Tesseract OCR wrapper when local tesseract executable is installed."""

    name = "tesseract_ocr"

    def _find_cmd(self) -> str | None:
        found = shutil.which("tesseract")
        if found:
            return found
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if Path(candidate).exists():
                return candidate
        return None

    def is_available(self) -> bool:
        try:
            import pytesseract  # noqa: F401

            return self._find_cmd() is not None
        except ImportError:
            return False

    def recognize(self, bgr: np.ndarray, variant_name: str = "raw") -> OcrEngineAttempt:
        start = time.perf_counter()
        if not self.is_available():
            return OcrEngineAttempt(
                engine_name=self.name,
                variant_name=variant_name,
                raw_text="",
                lines=[],
                mean_confidence=0.0,
                latency_ms=0.0,
            )
        import pytesseract

        cmd = self._find_cmd()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
        words: list[str] = []
        confs: list[float] = []
        for txt, conf in zip(data.get("text", []), data.get("conf", [])):
            t = str(txt).strip()
            try:
                c = float(conf)
            except (TypeError, ValueError):
                c = -1.0
            if t and c >= 0:
                words.append(t)
                confs.append(min(1.0, c / 100.0))

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        raw_text = " ".join(words)
        return OcrEngineAttempt(
            engine_name=self.name,
            variant_name=variant_name,
            raw_text=raw_text,
            lines=[raw_text] if raw_text else [],
            mean_confidence=round(sum(confs) / len(confs), 3) if confs else 0.0,
            latency_ms=round(elapsed_ms, 2),
        )


def get_available_engines() -> list[BaseOcrEngine]:
    """Return available OCR backends in priority order."""
    engines: list[BaseOcrEngine] = [
        RapidOcrEngine(),
        WindowsNativeOcrEngine(),
        TesseractOcrEngine(),
    ]
    return [engine for engine in engines if engine.is_available()]


class SmartStripOcrPipeline:
    """Runs quality check, preprocessing, multi-variant OCR, salt lookup, and fallback."""

    def __init__(
        self,
        primary_engine: BaseOcrEngine | None = None,
        salt_resolver: SaltResolver | None = None,
    ) -> None:
        self.salt_resolver = salt_resolver or SaltResolver()
        if primary_engine is not None:
            self.primary_engine = primary_engine
        else:
            available = get_available_engines()
            if not available:
                raise RuntimeError("No OCR backend available.")
            self.primary_engine = available[0]

    def scan_bytes(
        self,
        image_bytes: bytes,
        scan_id: str,
        bypass_quality_gate: bool = False,
        try_rotations: bool = True,
    ) -> StripScanResult:
        """Process raw strip image bytes in memory and resolve active salts."""
        bgr = decode_image_bytes(image_bytes)
        quality = inspect_image_quality(bgr, mode="strip")

        if not quality.passed and not bypass_quality_gate:
            return StripScanResult(
                scan_id=scan_id,
                quality_report=quality,
                retry_required=True,
                ocr_engine_used=None,
                raw_text="",
                attempts=[],
                resolved_medications=[],
                needs_manual_fallback=True,
                manual_suggestions=self.salt_resolver.search_brands_and_salts("", limit=6),
            )

        variants, applied_steps = enhance_strip_variants(bgr)
        quality.preprocessing_applied = applied_steps

        attempts: list[OcrEngineAttempt] = []
        best_meds: list[ResolvedMedication] = []
        best_raw = ""
        best_score = -1.0

        def _evaluate_candidate(img: np.ndarray, variant_label: str) -> bool:
            nonlocal best_meds, best_raw, best_score
            attempt = self.primary_engine.recognize(img, variant_name=variant_label)
            attempts.append(attempt)
            if not attempt.raw_text:
                return False
            meds, _ = self.salt_resolver.resolve_from_ocr_text(
                attempt.raw_text, engine_name=self.primary_engine.name
            )
            top_med_conf = meds[0].confidence if meds else 0.0
            composite = top_med_conf * 2.0 + attempt.mean_confidence * 0.4 + min(len(attempt.raw_text), 80) * 0.002
            if composite > best_score:
                best_score = composite
                best_raw = attempt.raw_text
                best_meds = meds
            return bool(meds and meds[0].confidence >= 0.90)

        candidate_order: list[tuple[str, np.ndarray]] = [
            ("enhanced_clahe", variants["enhanced_clahe"]),
            ("raw", bgr),
            ("illumination_flat_gray", variants["illumination_flat_gray"]),
            ("inverted_foil", variants["inverted_foil"]),
        ]

        confident_hit = False
        for label, img in candidate_order:
            if _evaluate_candidate(img, label):
                confident_hit = True
                break

        if not confident_hit and try_rotations:
            for angle in (90, 270, 180):
                rotated = rotate_image(variants["enhanced_clahe"], angle)
                if _evaluate_candidate(rotated, f"enhanced_clahe_rot{angle}"):
                    break

        needs_fallback = len(best_meds) == 0 or best_meds[0].confidence < 0.78
        manual_suggestions = (
            self.salt_resolver.search_brands_and_salts(best_raw[:40], limit=6)
            if needs_fallback
            else []
        )

        return StripScanResult(
            scan_id=scan_id,
            quality_report=quality,
            retry_required=False,
            ocr_engine_used=self.primary_engine.name,
            raw_text=best_raw,
            attempts=attempts,
            resolved_medications=best_meds,
            needs_manual_fallback=needs_fallback,
            manual_suggestions=manual_suggestions,
        )

    def benchmark_engines_on_image(
        self,
        image_bytes: bytes,
        engines: Sequence[BaseOcrEngine] | None = None,
    ) -> dict[str, dict[str, object]]:
        """Compare multiple OCR engines (raw vs preprocessed) on the same strip image."""
        bgr = decode_image_bytes(image_bytes)
        variants, _ = enhance_strip_variants(bgr)
        target_engines = list(engines) if engines is not None else get_available_engines()
        comparison: dict[str, dict[str, object]] = {}

        for engine in target_engines:
            raw_attempt = engine.recognize(bgr, variant_name="raw")
            enh_attempt = engine.recognize(variants["enhanced_clahe"], variant_name="enhanced_clahe")
            raw_meds, _ = self.salt_resolver.resolve_from_ocr_text(raw_attempt.raw_text, engine.name)
            enh_meds, _ = self.salt_resolver.resolve_from_ocr_text(enh_attempt.raw_text, engine.name)
            comparison[engine.name] = {
                "raw": {
                    "raw_text": raw_attempt.raw_text,
                    "latency_ms": raw_attempt.latency_ms,
                    "resolved_brands": [m.brand_name for m in raw_meds],
                    "resolved_salts": [s for m in raw_meds for s in m.active_salts],
                    "top_confidence": raw_meds[0].confidence if raw_meds else 0.0,
                },
                "enhanced": {
                    "raw_text": enh_attempt.raw_text,
                    "latency_ms": enh_attempt.latency_ms,
                    "resolved_brands": [m.brand_name for m in enh_meds],
                    "resolved_salts": [s for m in enh_meds for s in m.active_salts],
                    "top_confidence": enh_meds[0].confidence if enh_meds else 0.0,
                },
            }
        return comparison
