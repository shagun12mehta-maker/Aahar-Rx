# Aahar-Rx Backend Engineering Rulebook (GEMINI.md)

This rulebook defines the strict architectural, clinical safety, privacy compliance, and competition requirements for the **Aahar-Rx Backend API**. All backend code must rigorously adhere to the rules below.

---

## 1. Modular FastAPI Architecture (No Monoliths)
All backend functionality must be strictly decoupled across the following directory structure:

```text
aveshan2/
├── app/
│   ├── main.py                     # FastAPI app factory, CORS, middleware, router mount
│   ├── core/
│   │   ├── config.py               # Settings, environment variables, constants
│   │   └── consent_guard.py        # DPDP Act 2023 consent enforcement & validation
│   ├── api/
│   │   └── v1/
│   │       └── endpoints.py        # REST routes (/check-conflict, /generate-timetable, /consent)
│   ├── schemas/
│   │   └── clinical.py             # Pydantic v2 schemas for requests and responses
│   └── services/
│       └── conflict_engine.py      # Deterministic clinical evaluation & schedule logic
├── data/
│   └── verified_rules.json         # Audited clinical rule repository
└── tests/
    └── test_api.py                 # Pytest test suite for consent, conflict, and timetable APIs
```
*Rule:* **Never** combine endpoints, schemas, consent checks, and clinical logic into a single monolithic file. Each module must maintain a single responsibility.

---

## 2. Mandatory Clinical Safety Disclaimer
Every API response returned by `/check-conflict` and `/generate-timetable` (as well as related clinical endpoints) must explicitly include the standardized clinical disclaimer:

> **Clinical Disclaimer:** *"Aahar-Rx provides educational timing and dietary guidance only—it never advises skipping, altering, or replacing physician-prescribed medication dosages."*

*Rule:* The disclaimer must be an enforced field in response Pydantic models (`disclaimer: str`) so that no clinical response can ever be serialized without it.

---

## 3. Strict DPDP Act 2023 Consent Enforcement
In compliance with the **Digital Personal Data Protection (DPDP) Act 2023 (India)**:
- Every request that processes patient health data (medicine salts, scan outputs, meal items, schedule generation) must supply a valid `consent_id` in the request header (`X-Consent-ID`) or payload.
- The `app/core/consent_guard.py` dependency must verify that explicit user consent was captured and is active.
- If `consent_id` is missing, invalid, or expired, the API must immediately reject the request with **HTTP 403 Forbidden** and a structured error payload detailing consent requirements.

---

## 4. Strict Anonymity (ANVESHAN 2026 Rule 3)
To ensure compliance with ANVESHAN 2026 blind evaluation rules:
- **No student names**, **no mentor names**, and **no university/college/institution names or logos** may appear anywhere in code, docstrings, commit logs, API responses, or documentation.
- All attribution must refer strictly to team roles (e.g., `Lead Backend Engineer`, `Clinical Lead / Member 2`) and project name (`Aahar-Rx`).

---

## 5. Deterministic Execution & Zero AI Hallucination
- Clinical conflict detection and timetable calculation must execute strictly against audited datasets (`data/verified_rules.json`).
- LLM outputs are never used to dynamically generate dosages, contraindications, or time gaps.
