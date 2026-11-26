# Aahar-Rx Day 5 Privacy, Security & Blind-Review Audit (Member 4)

## 1. End-to-End Data Flow Audit

| Stage | Data Touched | Storage Behavior | Control Verified |
| --- | --- | --- | --- |
| 1. User Onboarding | `preferred_language`, `age_band` | Stored in `users` (`usr_*` random ID) | Zero personal identifiers collected |
| 2. Consent Capture | `consented`, `purpose`, `retention_policy` | Logged in `consent_logs` with UTC timestamp | `consented=false` blocked (`HTTP 403`) |
| 3. Scan Handoff | `active_salts`, `confirmed_foods`, `nutrient_flags` | Stored in `scan_records` (`confirmed_by_user=TRUE`) | Raw image fields rejected (`HTTP 422`); `raw_images_stored=0` enforced by SQL `CHECK` |
| 4. Conflict & Timetable | Rules from `data/verified_rules.json` + schedule slots | Persisted in `schedules` with safety disclaimer | Blocked if consent missing or withdrawn (`HTTP 403`) |
| 5. QR Health Pass | Compact active salts, safe slot times, swaps | Returned by `/api/v1/health-pass/{schedule_id}` | Contains zero PII (`user_id` excluded from QR pass) |
| 6. Erasure Request | `DELETE /api/v1/users/{user_id}/data` | Deletes `scan_records` & `schedules`; marks consent withdrawn | Subsequent reads/checks fail (`HTTP 403`) |

## 2. Security & Integrity Controls Checked
- **Deterministic Clinical Isolation:** Clinical conflict decisions come exclusively from Member 2's doctor-verified `data/verified_rules.json` seeded into SQLite/PostgreSQL—no generative LLM writes clinical dosage or interaction rules.
- **Strict Input Validation:** Pydantic v2 `ConfigDict(extra="forbid")`, `HH:MM` regex constraints, and parameterized SQL queries (`?` placeholders) prevent SQL injection and unexpected payload persistence.
- **ANVESHAN Rule 3 (Strict Blind-Review Anonymity):** Verified by automated test scan across `src/`, `db/`, `docs/`, `scripts/`, `tests/`, and `README.md` ensuring zero student, mentor, or institution names/logos appear anywhere in code, UI responses, or pitch materials.
