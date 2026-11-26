# Aahar-Rx Day 7 Final Packaging & ANVESHAN Submission Checklist (Member 4)

## 1. Functional Backend & Database Verification
- [x] PostgreSQL/Supabase migration script ready (`db/migrations/001_init_supabase_postgres.sql`)
- [x] Local SQLite repository auto-seeds `rules`, `salts`, `foods` from Member 2 `data/verified_rules.json`
- [x] `POST /api/v1/check-conflict` returns severity, IFCT evidence, absorption curve, and swaps
- [x] `POST /api/v1/generate-timetable` resolves multi-drug safe time gaps and outputs QR Health Pass JSON
- [x] `POST /api/v1/scans/ingest` accepts sanitized Member 1 scan handoff (no raw images)

## 2. DPDP Act 2023 & Clinical Safety Verification
- [x] Explicit consent recorded in `consent_logs` before processing health data (`HTTP 403` otherwise)
- [x] Raw image fields prohibited by strict Pydantic validation & DB `CHECK` constraint
- [x] Consent withdrawal (`POST /api/v1/consent/{id}/withdraw`) and user erasure (`DELETE /api/v1/users/{id}/data`) verified
- [x] Clinical safety disclaimer included on every response; never recommends altering/skipping prescribed doses

## 3. ANVESHAN 2026 Rule 3 (Strict Blind-Review Anonymity)
- [x] Zero student names in codebase, API docs, pitch deck, or generated PNG visuals
- [x] Zero university/institution names, logos, or watermarks
- [x] Zero mentor or faculty guide names

## 4. Reproducible Verification Commands
```powershell
python scripts/convert_and_validate.py
python scripts/run_clinical_scenarios.py
python -m pytest
python scripts/generate_pitch_visuals.py
python scripts/run_backend_e2e_demo.py
```
