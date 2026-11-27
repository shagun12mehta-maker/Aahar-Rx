"""
Aahar-Rx Backend Configuration & Constants
Centralized environment settings following GEMINI.md modular FastAPI architecture.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple


BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass(frozen=True)
class Settings:
    """Application settings loaded with safe local defaults."""

    app_title: str = os.getenv("AAHAR_APP_TITLE", "Aahar-Rx Clinical Guidance Engine API")
    app_version: str = os.getenv("AAHAR_APP_VERSION", "1.0.0")
    environment: str = os.getenv("AAHAR_ENV", "local")
    fastapi_port: int = int(os.getenv("AAHAR_API_PORT", "8000"))
    pwa_port: int = int(os.getenv("AAHAR_PWA_PORT", "8030"))
    verified_rules_path: str = os.getenv(
        "AAHAR_VERIFIED_RULES_PATH",
        os.path.join(BASE_DIR, "data", "verified_rules.json"),
    )
    allowed_cors_origins: Tuple[str, ...] = ("*",)


settings = Settings()
