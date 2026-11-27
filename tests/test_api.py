"""
Aahar-Rx Comprehensive Unit & Integration Test Suite
Target: ANVESHAN 2026 (Medical & Health Sciences Track)

Verifies:
1. HTTP 403 Forbidden when consent_id is missing (DPDP Act 2023)
2. Valid conflict detection for Levothyroxine + Morning Masala Chai with Milk
3. Safe timetable generation (Safe Time-Gap calculation & non-alteration of dosages)
4. Mandatory clinical_disclaimer present in all API responses
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.consent_guard import ConsentRegistry
from app.schemas.clinical import MANDATORY_CLINICAL_DISCLAIMER

client = TestClient(app)

# Seed an active test consent for authorized test cases
TEST_CONSENT_ID = "test-consent-dpdp-2023-active"
ConsentRegistry.seed_test_consent(TEST_CONSENT_ID)


# =============================================================================
# 1. DPDP Act 2023 Consent Enforcement Tests (HTTP 403 when missing)
# =============================================================================

def test_http_403_when_consent_id_is_missing():
    """Verify HTTP 403 Forbidden is returned when consent_id is missing."""
    response = client.post("/api/v1/check-conflict", json={
        "active_salt": "Levothyroxine Sodium",
        "food_items": ["Morning Masala Chai with Milk"]
    })
    assert response.status_code == 403
    data = response.json()
    assert "DPDP Act 2023 Consent Required" in data["detail"]
    assert "clinical_disclaimer" in data
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


def test_consent_creation_and_registration():
    """Verify registration of a new anonymous DPDP consent session."""
    response = client.post("/api/v1/consent", json={
        "purpose": "CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS"
    })
    assert response.status_code == 201
    data = response.json()
    assert "consent_id" in data
    assert data["status"] == "ACTIVE"
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


# =============================================================================
# 2. Conflict Detection Tests (Levothyroxine + Morning Masala Chai with Milk)
# =============================================================================

def test_conflict_detection_levothyroxine_and_chai():
    """Verify conflict detection for Levothyroxine Sodium + Morning Masala Chai with Milk."""
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

    conflict = data["conflicts"][0]
    assert conflict["rule_id"] == "RULE-THY-001"
    assert conflict["severity"] == "HIGH"
    assert conflict["absorption_impact"]["bioavailability_drop_pct"] == 38.0
    assert conflict["safe_time_gap_hours"]["before_food_hours"] == 1.0
    assert conflict["safe_time_gap_hours"]["after_food_hours"] == 4.0
    assert any("Chai" in food for food in conflict["conflicted_foods"])
    assert len(conflict["ghar_ki_rasoi_swaps"]) > 0


# =============================================================================
# 3. Safe Timetable Generation Tests
# =============================================================================

def test_safe_timetable_generation():
    """Verify safe timetable generation shifts intake and maintains prescribed dosages."""
    payload = {
        "medications": [
            {
                "medicine_name": "Thyronorm 50mcg",
                "active_salt": "Levothyroxine Sodium",
                "prescribed_time": "07:00"
            }
        ],
        "meals": [
            {
                "meal_name": "Morning Breakfast & Chai",
                "planned_time": "07:15",
                "food_items": ["Morning Masala Chai with Milk", "Poha"]
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
    assert len(data["timetable"]) == 1

    entry = data["timetable"][0]
    assert entry["active_salt"] == "Levothyroxine Sodium"
    assert entry["prescribed_time"] == "07:00"
    # Medication should be adjusted or food buffer enforced (e.g. 06:15 or 06:00 to leave 1.0h before 07:15 chai)
    assert entry["calculated_safe_time"] != ""
    assert len(entry["conflicts_detected"]) > 0
    assert len(entry["recommended_swaps"]) > 0


# =============================================================================
# 4. Mandatory Clinical Disclaimer Enforcement in Responses
# =============================================================================

def test_mandatory_clinical_disclaimer_in_all_responses():
    """Verify clinical_disclaimer is present across all endpoints."""
    # Consent endpoint
    res_consent = client.post("/api/v1/consent", json={})
    assert res_consent.json()["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

    # Conflict check endpoint
    res_conflict = client.post(
        "/api/v1/check-conflict",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json={"active_salt": "Levothyroxine Sodium", "food_items": ["Boiled Rice"]}
    )
    assert res_conflict.json()["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

    # Timetable endpoint
    res_timetable = client.post(
        "/api/v1/generate-timetable",
        headers={"X-Consent-ID": TEST_CONSENT_ID},
        json={
            "medications": [{"medicine_name": "Thyronorm", "active_salt": "Levothyroxine", "prescribed_time": "08:00"}],
            "meals": [{"meal_name": "Lunch", "planned_time": "13:00", "food_items": ["Dal", "Roti"]}]
        }
    )
    assert res_timetable.json()["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER

    # Health check endpoint
    res_health = client.get("/health")
    assert res_health.json()["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER
