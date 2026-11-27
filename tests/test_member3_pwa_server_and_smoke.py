"""Integration tests for Member 3 PWA handler and optional in-memory Member 1 scan bridge."""

from __future__ import annotations

import io
import json
from pathlib import Path

from scripts.serve_member3_pwa import Member3PwaHandler
from tests.fixtures.generate_test_assets import generate_meal_image_bytes, generate_strip_image_bytes

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


class _MockSocket:
    """In-memory socket adapter so handler GET/POST tests run without binding a TCP port."""

    def __init__(self, raw_request: bytes) -> None:
        self._rfile = io.BytesIO(raw_request)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        return self._rfile if "r" in mode else self._wfile

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def close(self) -> None:
        pass


class _TestHandler(Member3PwaHandler):
    def __init__(self, raw_request: bytes) -> None:
        self._sock = _MockSocket(raw_request)
        super().__init__(self._sock, ("127.0.0.1", 0), None, directory=str(FRONTEND_DIR))

    @property
    def raw_response(self) -> bytes:
        return self._sock._wfile.getvalue()


def _dispatch(method: str, path: str, body: bytes = b"", content_type: str = "") -> tuple[int, dict[str, str], bytes]:
    headers = [f"{method} {path} HTTP/1.1", "Host: 127.0.0.1"]
    if body:
        headers.append(f"Content-Length: {len(body)}")
        if content_type:
            headers.append(f"Content-Type: {content_type}")
    headers.append("Connection: close")
    raw_req = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body

    handler = _TestHandler(raw_req)
    raw_resp = handler.raw_response
    head, payload = raw_resp.split(b"\r\n\r\n", 1)
    head_lines = head.decode("latin1").splitlines()
    status_code = int(head_lines[0].split()[1])
    resp_headers = {}
    for line in head_lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            resp_headers[k.strip().lower()] = v.strip()
    return status_code, resp_headers, payload


def test_member3_pwa_static_assets_and_local_scan_bridge() -> None:
    for route in (
        "/",
        "/css/tokens.css",
        "/css/app.css",
        "/assets/aahar-rx-mark.svg",
        "/assets/aahar-rx-icon.jpg",
        "/data/i18n.json",
        "/data/pk_profiles.json",
        "/data/rules_bundle.json",
        "/data/voice_scripts.json",
        "/data/ux_voice_alerts.json",
        "/audio/hi/RULE-THY-001.mp3",
        "/audio/mr/RULE-THY-001.mp3",
        "/audio/hi/ALERT-REFILL.mp3",
        "/audio/mr/ALERT-HIGH-RISK.mp3",
        "/vendor/qrcode.min.js",
    ):
        status, _, body = _dispatch("GET", route)
        assert status == 200, f"Unexpected HTTP status {status} on {route}"
        assert len(body) > 100

    status, _, health_raw = _dispatch("GET", "/api/health")
    assert status == 200
    health = json.loads(health_raw.decode("utf-8"))
    assert health["ok"] is True
    assert health["bridge"] == "member1_smart_scan"
    assert health["raw_images_retained"] is False

    clean_strip = generate_strip_image_bytes("01_thyronorm_clean")
    status, _, strip_raw = _dispatch("POST", "/api/local-scan/strip", body=clean_strip, content_type="image/png")
    assert status == 200
    strip_out = json.loads(strip_raw.decode("utf-8"))
    assert strip_out["retry_required"] is False
    assert strip_out["medications"][0]["brand_name"] == "Thyronorm"
    assert strip_out["medications"][0]["expiry_date"] == "2027-08"
    assert strip_out["medications"][0]["tablet_count"] == 30

    blur_strip = generate_strip_image_bytes("15_fail_severe_blur")
    status, _, blur_raw = _dispatch("POST", "/api/local-scan/strip", body=blur_strip, content_type="image/png")
    assert status == 200
    blur_out = json.loads(blur_raw.decode("utf-8"))
    assert blur_out["retry_required"] is True
    assert len(blur_out["retry_guidance"]) >= 1

    chai_img = generate_meal_image_bytes("morning_chai_with_milk")
    status, _, meal_raw = _dispatch(
        "POST",
        "/api/local-scan/meal?meal_slot=early_morning_empty_stomach",
        body=chai_img,
        content_type="image/png",
    )
    assert status == 200
    meal_out = json.loads(meal_raw.decode("utf-8"))
    assert meal_out["retry_required"] is False
    assert "chai_with_milk" in meal_out["detected_food_ids"]
