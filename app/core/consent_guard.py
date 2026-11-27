"""
DPDP Act 2023 Consent Guard Dependency
Validates active consent before processing health or dietary data.
Returns HTTP 403 Forbidden if consent is missing or invalid.
"""

from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
import uuid
from fastapi import Header, HTTPException, Request, status

class ConsentRegistry:
    """In-memory DPDP Act 2023 consent session store with TTL validation."""
    _sessions: Dict[str, dict] = {}

    @classmethod
    def register_consent(cls, purpose: str = "CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS", duration_hours: int = 24) -> dict:
        consent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        valid_until = now + timedelta(hours=duration_hours)
        
        record = {
            "consent_id": consent_id,
            "purpose": purpose,
            "status": "ACTIVE",
            "granted_at": now.isoformat(),
            "valid_until": valid_until.isoformat(),
            "dpdp_compliant": True
        }
        cls._sessions[consent_id] = record
        return record

    @classmethod
    def is_valid(cls, consent_id: Optional[str]) -> bool:
        if not consent_id or not consent_id.strip():
            return False
        record = cls._sessions.get(consent_id.strip())
        if not record:
            # For testing convenience and mock frontend tokens, accept recognized prefixes or UUID shapes if pre-seeded
            return False
        if record.get("status") != "ACTIVE":
            return False
        valid_until = datetime.fromisoformat(record["valid_until"])
        if datetime.now(timezone.utc) > valid_until:
            record["status"] = "EXPIRED"
            return False
        return True

    @classmethod
    def seed_test_consent(cls, consent_id: str) -> None:
        """Helper to seed test consents for automated test suites."""
        cls._sessions[consent_id] = {
            "consent_id": consent_id,
            "purpose": "TEST_SUITE_EVALUATION",
            "status": "ACTIVE",
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "dpdp_compliant": True
        }


async def verify_consent(
    request: Request,
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-ID")
) -> str:
    """
    FastAPI dependency enforcing DPDP Act 2023 consent validation.
    Extracts consent_id from header (X-Consent-ID) or JSON body (consent_id).
    Raises HTTP 403 Forbidden if consent_id is missing, invalid, or expired.
    """
    consent_id = x_consent_id

    # If not in header, try reading from JSON body
    if not consent_id:
        try:
            body = await request.json()
            if isinstance(body, dict):
                consent_id = body.get("consent_id")
        except Exception:
            pass

    if not consent_id or not str(consent_id).strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "DPDP Act 2023 Consent Required: Missing consent_id. "
                "Provide a valid consent_id via 'X-Consent-ID' header or 'consent_id' body field "
                "before processing health, prescription, or dietary data."
            )
        )

    clean_id = str(consent_id).strip()
    if not ConsentRegistry.is_valid(clean_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"DPDP Act 2023 Consent Violation: Consent ID '{clean_id}' is invalid, revoked, or expired. "
                "Request a new consent session via POST /api/v1/consent."
            )
        )

    return clean_id
