"""
Aahar-Rx Comprehensive Unit & Integration Test Suite
Target: ANVESHAN 2026 (Medical & Health Sciences Track)

Verifies:
1. DPDP Act 2023 Consent Guard (HTTP 403 enforcement for patient & doctor consent)
2. Conflict detection for Levothyroxine + Morning Masala Chai with Milk
3. Safe timetable generation (Safe Time-Gap calculation & non-alteration of dosages)
4. NEW FLOW 1: High-Risk Clash Report generation + Jitsi Meet WebRTC room with separate Doctor Consent gate
5. NEW FLOW 2: Routine Shift Engine - Late-meal alarm recalculation & FCM notification payload
6. NEW FLOW 3: Medicine Box - Stock & expiry tracking with 3-day low-stock alert & 1mg deep-link
7. Mandatory updated clinical_disclaimer present across all API responses
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.consent_guard import ConsentRegistry
from app.schemas.clinical import MANDATORY_CLINICAL_DISCLAIMER

client = TestClient(app)

# Seed test consent tokens
TEST_PATIENT_CONSENT_ID = "test-consent-dpdp-patient-2023"
TEST_DOCTOR_SHARE_CONSENT_ID = "test-consent-dpdp-doctor-share-2023"

ConsentRegistry.seed_test_consent(TEST_PATIENT_CONSENT_ID, consent_type="PATIENT_PROCESSING")
ConsentRegistry.seed_test_consent(TEST_DOCTOR_SHARE_CONSENT_ID, consent_type="DOCTOR_SHARE")


# =============================================================================
# 1. DPDP Act 2023 Consent Enforcement Tests (HTTP 403 when missing)
# =============================================================================

def test_http_403_when_consent_id_is_missing():
    """Verify HTTP 403 Forbidden is returned when patient consent_id is missing."""
    response = client.post("/api/v1/check-conflict", json={
        "active_salt": "Levothyroxine Sodium",
        "food_items": ["Morning Masala Chai with Milk"]
    })
    assert response.status_code == 403
    data = response.json()
    assert "DPDP Act 2023 Consent Required" in data["detail"]
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


def test_consent_creation_and_registration():
    """Verify registration of a new anonymous DPDP consent session."""
    response = client.post("/api/v1/consent", json={
        "purpose": "CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS",
        "consent_type": "PATIENT_PROCESSING"
    })
    assert response.status_code == 201
    data = response.json()
    assert "consent_id" in data
    assert data["status"] == "ACTIVE"
    assert data["consent_type"] == "PATIENT_PROCESSING"
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
        headers={"X-Consent-ID": TEST_PATIENT_CONSENT_ID},
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
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


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
        headers={"X-Consent-ID": TEST_PATIENT_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_medications"] == 1
    assert len(data["timetable"]) == 1

    entry = data["timetable"][0]
    assert entry["active_salt"] == "Levothyroxine Sodium"
    assert entry["prescribed_time"] == "07:00"
    assert entry["calculated_safe_time"] != ""
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


# =============================================================================
# 4. NEW FLOW 1: High-Risk Clash Report with Separate Doctor Consent Gate
# =============================================================================

def test_clash_report_blocked_without_doctor_consent():
    """Verify HTTP 403 is returned if doctor_share_consent_id is missing or patient-only."""
    # Attempting with regular patient consent instead of DOCTOR_SHARE consent
    response = client.post(
        "/api/v1/clash-report",
        headers={"X-Doctor-Consent-ID": TEST_PATIENT_CONSENT_ID},
        json={
            "active_salt": "Levothyroxine Sodium",
            "conflicted_food": "Morning Masala Chai with Milk"
        }
    )
    assert response.status_code == 403
    assert "Doctor Data-Sharing Consent" in response.json()["detail"] or "Consent Violation" in response.json()["detail"]


def test_clash_report_success_with_doctor_consent():
    """Verify shareable report token and Jitsi Meet room generation under valid doctor consent."""
    response = client.post(
        "/api/v1/clash-report",
        headers={"X-Doctor-Consent-ID": TEST_DOCTOR_SHARE_CONSENT_ID},
        json={
            "active_salt": "Levothyroxine Sodium",
            "conflicted_food": "Morning Masala Chai with Milk"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["report_token"].startswith("REP-")
    assert "https://meet.jit.si/aahar-rx-consult-" in data["jitsi_room_url"]
    assert data["anonymized_doctor_id"].startswith("DR-MED-")
    assert data["severity"] == "HIGH"
    assert data["bioavailability_drop_pct"] == 38.0
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


# =============================================================================
# 5. NEW FLOW 2: Routine Shift Engine (Delayed Meal Alarm Recalculation)
# =============================================================================

def test_routine_shift_engine_delayed_meal():
    """Verify automatic recalculation of alarms when meal is delayed."""
    # Metformin taken post-meal: lunch delayed from 13:00 to 14:15
    payload = {
        "medicine_name": "Glycomet 500",
        "active_salt": "Metformin Hydrochloride",
        "scheduled_time": "13:00",
        "meal_anchor": "Lunch",
        "delayed_meal_time": "14:15"
    }
    response = client.post(
        "/api/v1/shift-alarm",
        headers={"X-Consent-ID": TEST_PATIENT_CONSENT_ID},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["shifted_alarm_time"] == "14:15"
    assert data["shift_minutes"] == 75
    assert "fcm_payload" in data
    assert data["fcm_payload"]["data"]["new_alarm_time"] == "14:15"
    assert data["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


# =============================================================================
# 6. NEW FLOW 3: Medicine Box (Stock Tracking, 3-Day Alert & 1mg Deep-link)
# =============================================================================

def test_medicine_box_stock_tracking_and_low_stock_alert():
    """Verify inventory registration, dose consumption, and 3-day low-stock alert."""
    # Step 1: Register medicine with 5 tablets, 1 per day
    reg_response = client.post(
        "/api/v1/medicine-box",
        headers={"X-Consent-ID": TEST_PATIENT_CONSENT_ID},
        json={
            "brand": "Thyronorm 50mcg",
            "salt": "Levothyroxine Sodium",
            "expiry_date": "2027-12-31",
            "initial_count": 5,
            "daily_dosage_count": 1
        }
    )
    assert reg_response.status_code == 201
    item = reg_response.json()
    item_id = item["item_id"]
    assert item["remaining_count"] == 5
    assert item["days_of_stock_left"] == 5
    assert item["low_stock_alert"] is False
    assert "1mg.com/search" in item["reorder_url"]

    # Step 2: Consume 3 doses -> 2 tablets remaining (<= 3 days supply)
    consume_response = client.post(
        f"/api/v1/medicine-box/{item_id}/consume",
        headers={"X-Consent-ID": TEST_PATIENT_CONSENT_ID},
        json={"doses_consumed": 3}
    )
    assert consume_response.status_code == 200
    updated_item = consume_response.json()
    assert updated_item["remaining_count"] == 2
    assert updated_item["days_of_stock_left"] == 2
    # Must trigger low_stock_alert
    assert updated_item["low_stock_alert"] is True
    assert "LOW STOCK ALERT" in updated_item["alert_message"]
    assert "Thyronorm" in updated_item["reorder_url"]
    assert updated_item["clinical_disclaimer"] == MANDATORY_CLINICAL_DISCLAIMER


# =============================================================================
# 7. Mandatory Updated Clinical Disclaimer Verification
# =============================================================================

def test_mandatory_updated_clinical_disclaimer():
    """Verify the exact updated clinical disclaimer text is present."""
    expected_disclaimer = (
        "Aahar-Rx provides timing and dietary guidance only. "
        "The app never advises skipping, altering, or replacing prescribed medication dosages. "
        "Any dose or medicine change is made only by a licensed doctor, through the Doctor Video Consult."
    )
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["clinical_disclaimer"] == expected_disclaimer
