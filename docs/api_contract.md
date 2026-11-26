# Aahar-Rx REST API & Database Contract (Member 4)

> **Clinical Safety Notice:** Aahar-Rx provides timing and dietary guidance only. It never advises skipping, altering, or replacing prescribed medication dosages.
> **Privacy Standard:** Built under **DPDP Act 2023** guidelines (explicit consent before processing, minimal retention, zero raw photo storage).

---

## 1. Relational Database Schema v1 (`db/migrations/001_init_supabase_postgres.sql`)

| Table | Purpose | Key Columns |
| --- | --- | --- |
| `users` | Pseudonymous user sessions (no PII) | `user_id`, `preferred_language` (`en`/`hi`/`mr`), `age_band`, `erased_at_utc` |
| `consent_logs` | Immutable DPDP consent ledger | `consent_id`, `user_id`, `consented`, `purpose`, `retention_policy`, `raw_images_stored=FALSE`, `withdrawn_at_utc` |
| `salts` | Active pharmaceutical ingredients | `salt_id`, `salt_name`, `drug_class`, `rule_ids` |
| `foods` | Indian foods + IFCT 2017 metadata | `food_id`, `food_name`, `ifct_code`, `primary_nutrients`, `clinical_note` |
| `rules` | Member 2 doctor-verified rules | `rule_id`, `active_salts`, `culprit_indian_foods`, `before_food_hours`, `after_food_hours`, `bioavailability_drop_pct`, `ghar_ki_rasoi_swaps`, `citations`, `clinical_sign_off` |
| `scan_records` | Sanitized Member 1 scan outputs | `scan_id`, `user_id`, `consent_id`, `active_salts`, `confirmed_foods`, `nutrient_flags`, `confirmed_by_user=TRUE` |
| `schedules` | Generated safe timetables & QR payloads | `schedule_id`, `user_id`, `timeline`, `qr_health_pass`, `safety_disclaimer` |

---

## 2. REST Endpoints (FastAPI)

| Method & Path | Consumer | Purpose |
| --- | --- | --- |
| `GET /health` | All | Health probe, loaded verified rules count, DPDP & Rule 3 status |
| `POST /api/v1/users` | Member 3 UI | Create pseudonymous user (`en`/`hi`/`mr`) |
| `POST /api/v1/consent` | Member 3 UI | Record explicit DPDP Act 2023 consent (`consented=false` returns HTTP `403`) |
| `GET /api/v1/consent/{consent_id}` | Audit / UI | Inspect consent status |
| `POST /api/v1/consent/{consent_id}/withdraw` | Member 3 UI | Withdraw consent immediately (blocks future scans/conflicts) |
| `DELETE /api/v1/users/{user_id}/data` | Member 3 UI | DPDP Right to Erasure: purges user scans, schedules, and marks consents withdrawn |
| `GET /api/v1/rules`, `/salts`, `/foods` | Member 1 & 3 | Fetch DB-seeded verified clinical rules, salts, and IFCT foods |
| `POST /api/v1/scans/ingest` | Member 1 | Store sanitized active salts & user-confirmed foods (`extra="forbid"` rejects raw image blobs) |
| `POST /api/v1/check-conflict` | Member 3 UI | Deterministic conflict lookup + IFCT evidence + Ghar-Ki-Rasoi swaps + PK curve points |
| `POST /api/v1/generate-timetable` | Member 3 UI | Multi-drug safe time-gap daily schedule + compact QR Health Pass JSON |
| `GET /api/v1/schedules/{schedule_id}` | Member 3 UI | Retrieve saved timetable |
| `GET /api/v1/health-pass/{schedule_id}` | Member 3 QR | Retrieve zero-PII QR Health Pass JSON for `qrcode.react` |
| `GET /api/v1/privacy/audit-summary` | Audit / Pitch | Verify `raw_images_stored_count == 0`, active consents, and rules loaded |
