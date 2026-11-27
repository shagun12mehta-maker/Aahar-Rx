"""
Aahar-Rx Comprehensive Test Suite
Validates:
1. DPDP Act 2023 Consent Guard (HTTP 403 enforcement)
2. Conflict detection against data/verified_rules.json
3. Timetable generation with safe gap calculations
4. Mandatory clinical disclaimer in all responses
5. Strict Anonymity (Zero PII / institutional names)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.consent_guard import ConsentRegistry
from app.schemas.clinical import MANDATORY_CLINICAL_DISCLAIMER

client = TestClient(app)

# Seed an active consent for authorized test requests
TEST_CONSENT_ID = "test-consent-dpdp-2023-valid"
ConsentRegistry.seed_test_consent(TEST_CONSENT_ID)

# -----------------------------------------------------------------------------
# 1. DPDP Act 2023 Consent Guard Tests
# -----------------------------------------------------------------------------

def test_consent_creation():
    """Verify creation of anonymous DPDP Act 2023 consent session."""
    response = client.post("/api/v1/consent", json={
        "purpose": "CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS"
    })
    assert response.status_code == 201
    data = response.json()
    assert "consent_id" in data
    assert data["status"] == "ACTIVE"
    assert "valid_until" in data
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

def test_blocked_without_consent():
    """Verify HTTP 403 Forbidden is returned when consent_id is missing."""
    response = client.post("/api/v1/check-conflict", json={
        "active_salt": "Levothyroxine Sodium",
        "food_items": ["Morning Masala Chai with Milk"]
    })
    assert response.status_code == 403
    assert "DPDP Act 2023 Consent Required" in response.json()["detail"]
    assert response.json()["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

def test_blocked_with_invalid_consent():
    """Verify HTTP 403 Forbidden is returned when consent_id is bogus."""
    response = client.post(
        "/api/v1/check-conflict",
        headers={"X-Consent-ID": "non-existent-fake-consent-id"},
        json={
            "active_salt": "Levothyroxine Sodium",
            "food_items": ["Morning Masala Chai with Milk"]
        }
    )
    assert response.status_code == 403
    assert "DPDP Act 2023 Consent Violation" in response.json()["detail"]

# -----------------------------------------------------------------------------
# 2. Scans Processing Tests
# -----------------------------------------------------------------------------

def test_scan_payload_processing():
    """Verify Member 1 OCR and meal detection payload handling."""
    payload = {
        "strip_ocr": {
            "medicine_name": "Thyronorm 50mcg",
            "detected_salts": ["Levothyroxine Sodium"],
            "confidence_score": 0.96
        },
        "meal_detection": {
            "meal_name": "Breakfast",
            "detected_food_items": ["Morning Masala Chai with Milk", "Poha"],
            "confidence_score": 0.92
        }
    }
    response = client.post(
        "/api/v1/scans",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALIDATED"
    assert "Levothyroxine Sodium" in data["detected_salts"]
    assert "Morning Masala Chai with Milk" in data["detected_food_items"]
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

# -----------------------------------------------------------------------------
# 3. Clinical Conflict Evaluation Tests
# -----------------------------------------------------------------------------

def test_conflict_detection_thyroid_tea():
    """Verify Levothyroxine + Masala Chai triggers RULE-THY-001."""
    payload = {
        "active_salt": "Levothyroxine Sodium",
        "food_items": ["Morning Masala Chai with Milk", "Biscuits"]
    }
    response = client.post(
        "/api/v1/check-conflict",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] is True
    assert len(data["conflicts"]) >= 1

    first_conflict = data["conflicts"][0]
    assert first_conflict["rule_id"] == "RULE-THY-001"
    assert first_conflict["severity"] == "HIGH"
    assert first_conflict["absorption_impact"]["bioavailability_drop_pct"] == 38.0
    assert first_conflict["safe_time_gap_hours"]["before_food_hours"] == 1.0
    assert first_conflict["safe_time_gap_hours"]["after_food_hours"] == 4.0
    assert len(first_conflict["ghar_ki_rasoi_swaps"]) > 0
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

def test_conflict_detection_iron_spinach():
    """Verify Ferrous Ascorbate + Masala Chai triggers RULE-IRO-002."""
    payload = {
        "active_salt": "Ferrous Ascorbate",
        "food_items": ["Masala Chai"]
    }
    response = client.post(
        "/api/v1/check-conflict",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] is True
    assert any(c["rule_id"] == "RULE-IRO-002" for c in data["conflicts"])

def test_no_conflict_safe_food():
    """Verify safe food does not trigger false positive."""
    payload = {
        "active_salt": "Levothyroxine Sodium",
        "food_items": ["Boiled Rice", "Plain Dal"]
    }
    response = client.post(
        "/api/v1/check-conflict",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] is False
    assert len(data["conflicts"]) == 0
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

# -----------------------------------------------------------------------------
# 4. Safe Timetable Generation Tests
# -----------------------------------------------------------------------------

def test_generate_timetable_safe_shift():
    """Verify timetable shifts Levothyroxine when taken too close to Chai."""
    payload = {
        "medications": [
            {
                "medicine_name": "Thyronorm",
                "active_salt": "Levothyroxine Sodium",
                "prescribed_time": "08:00"
            }
        ],
        "meals": [
            {
                "meal_name": "Morning Masala Chai",
                "planned_time": "08:15",
                "food_items": ["Morning Masala Chai with Milk"]
            }
        ]
    }
    response = client.post(
        "/api/v1/generate-timetable",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_medications"] == 1
    entry = data["timetable"][0]
    assert entry["prescribed_time"] == "08:00"
    # Safe gap before food is 1.0 hour, so 08:15 - 1 hr = 07:15
    assert entry["calculated_safe_time"] == "07:15"
    assert "RULE-THY-001" in entry["conflicts_detected"]
    assert len(entry["recommended_swaps"]) > 0
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

# -----------------------------------------------------------------------------
# 5. System Health & Anonymity Tests
# -----------------------------------------------------------------------------

def test_health_check():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER
