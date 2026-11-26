"""Lightweight local PWA preview server for Member 3 with optional in-memory Member 1 scan bridge."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aahar_scan import AaharSmartScanPipeline, create_scan_consent  # noqa: E402

_PIPELINE: AaharSmartScanPipeline | None = None


def _get_pipeline() -> AaharSmartScanPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = AaharSmartScanPipeline()
    return _PIPELINE


class Member3PwaHandler(SimpleHTTPRequestHandler):
    """Serve static frontend assets cleanly plus optional in-memory Member 1 camera bridge."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".webmanifest": "application/manifest+json; charset=utf-8",
        ".mp3": "audio/mpeg",
        ".svg": "image/svg+xml",
        ".png": "image/png",
    }

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?")[0] == "/api/health":
            self._send_json({"ok": True, "bridge": "member1_smart_scan", "raw_images_retained": False})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?")[0]
        if route not in ("/api/local-scan/strip", "/api/local-scan/meal"):
            self._send_json({"error": "Not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 12 * 1024 * 1024:
            self._send_json({"error": "Invalid image payload size"}, status=400)
            return

        image_bytes = self.rfile.read(length)
        consent = create_scan_consent(consented=True)
        pipeline = _get_pipeline()

        if route == "/api/local-scan/strip":
            res = pipeline.scan_medicine_strip(image_bytes=image_bytes, consent=consent)
            self._send_json(
                {
                    "retry_required": res.retry_required,
                    "retry_guidance": res.quality_report.retry_guidance,
                    "medications": [m.model_dump(mode="json") for m in res.resolved_medications],
                }
            )
            return

        parsed = urlsplit(self.path)
        query_params = parse_qs(parsed.query)
        raw_slot = (query_params.get("meal_slot") or ["lunch"])[0]
        allowed_slots = {
            "early_morning_empty_stomach",
            "breakfast",
            "mid_morning",
            "lunch",
            "evening_chai_snack",
            "dinner",
            "bedtime",
        }
        meal_slot = raw_slot if raw_slot in allowed_slots else "lunch"

        meal_res = pipeline.scan_meal_photo(
            image_bytes=image_bytes,
            consent=consent,
            meal_slot=meal_slot,  # type: ignore[arg-type]
        )
        self._send_json(
            {
                "retry_required": meal_res.retry_required,
                "retry_guidance": meal_res.quality_report.retry_guidance,
                "detected_food_ids": [d.canonical_food_id for d in meal_res.suggested_items],
            }
        )


def start_server(host: str = "127.0.0.1", port: int = 8030) -> ThreadingHTTPServer:
    """Create and bind the Member 3 PWA HTTP server."""
    handler = partial(Member3PwaHandler, directory=str(FRONTEND_DIR))
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Aahar-Rx Member 3 PWA frontend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8030)
    args = parser.parse_args()

    server = start_server(host=args.host, port=args.port)
    print(f"Serving Aahar-Rx Member 3 PWA at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
