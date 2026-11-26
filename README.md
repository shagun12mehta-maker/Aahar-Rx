# Aahar-Rx

> **Food-Drug Interaction & Safe Time-Gap Guidance System**  
> *Target: ANVESHAN 2026 (Medical & Health Sciences Track)*  
> *Compliance: Strict Anonymity (Rule 3) & DPDP Act 2023 Guidelines*
>
> **Clinical Safety Notice:** Aahar-Rx provides timing and dietary guidance only. It never advises skipping, altering, or replacing prescribed medication dosages. Always follow your prescribing physician's instructions.

---

## Overview
Aahar-Rx bridges clinical pharmacology with authentic Indian dietary practices. In India, polypharmacy patients frequently suffer from therapeutic failure or toxicity due to unaddressed drug-nutrient interactions (e.g., taking Levothyroxine with milky masala tea, or taking Iron supplements with polyphenol-rich meals).

Aahar-Rx detects these conflicts through medicine strip OCR and meal photo analysis, calculates evidence-backed **Safe Time Gaps**, and offers **"Ghar-Ki-Rasoi"** practical kitchen swaps without altering physician-prescribed dosages.

---

## Repository Structure

```text
Aahar-Rx/
├── data/
│   ├── verified_rules.json          # Primary clinical rules dataset (Member 2)
│   └── clinical_rules.csv           # Tabular dataset for clinical review (Member 2)
├── db/
│   └── migrations/
│       └── 001_init_supabase_postgres.sql  # Supabase/PostgreSQL schema v1 + RLS (Member 4)
├── docs/
│   ├── api_contract.md              # REST API & schema contract (Member 4)
│   ├── dpdp_privacy_compliance.md   # DPDP Act 2023 consent & retention guide (Member 4)
│   ├── privacy_security_audit.md    # Privacy, security & Rule 3 audit (Member 4)
│   ├── live_demo_script.md          # End-to-end stage demo script (Member 4)
│   ├── master_pitch_deck.md         # Master ANVESHAN pitch deck content (Member 4)
│   ├── submission_checklist.md      # Final Day 7 packaging checklist (Member 4)
│   ├── doctor_review_packet.md      # Clinical review summary & physician sign-off (Member 2)
│   └── pitch_slides_and_defense.md  # Methodology & presentation defense notes (Member 2)
├── reports/
│   ├── system_architecture_and_dpdp.png
│   └── absorption_curve_and_timetable.png
├── scripts/
│   ├── convert_and_validate.py      # CSV to JSON schema validator & converter (Member 2)
│   ├── run_clinical_scenarios.py    # Clinical scenario validator (Member 2)
│   ├── test_conflict_engine.py      # Reference conflict prototype (Member 2)
│   ├── generate_pitch_visuals.py    # Generates ANVESHAN pitch visual cards (Member 4)
│   └── run_backend_e2e_demo.py      # End-to-end backend & DPDP demo runner (Member 4)
├── src/aahar_backend/               # FastAPI Backend, DPDP DB, Conflict & Timetable Engines (Member 4)
├── tests/                           # Automated backend, conflict, DB, and DPDP tests (Member 4)
└── README.md
```

---

## Backend, Safety & Pitch Architecture (Member 4 Deliverables)

- **FastAPI Backend (`src/aahar_backend/api.py`)**:
  - `POST /api/v1/users`, `POST /api/v1/consent`, `POST /api/v1/consent/{id}/withdraw`, `DELETE /api/v1/users/{id}/data`
  - `POST /api/v1/scans/ingest` (sanitized Member 1 handoff—zero raw image bytes accepted)
  - `POST /api/v1/check-conflict` (deterministic Member 2 rule lookup + IFCT evidence + pharmacokinetic absorption curves + Ghar-Ki-Rasoi swaps)
  - `POST /api/v1/generate-timetable` (multi-drug daily safe schedule + 1-Click QR Health Pass payload for Member 3)
  - `GET /api/v1/rules`, `/salts`, `/foods`, `/schedules/{id}`, `/health-pass/{id}`, `/api/v1/privacy/audit-summary`
- **Database (`db/migrations/001_init_supabase_postgres.sql` & `src/aahar_backend/db.py`)**:
  - Supabase/PostgreSQL v1 DDL + local SQLite repository seeded automatically from Member 2's `data/verified_rules.json`.
- **DPDP Act 2023 & Blind-Review Guardrails**:
  - DB-enforced active consent prior to processing (`HTTP 403` if missing/withdrawn), schema-level rejection of raw image payloads (`HTTP 422`), full right-to-erasure endpoint, and strict ANVESHAN Rule 3 anonymity.

### Quickstart (Backend & Verification)

```powershell
python -m pip install -r requirements.txt
python scripts/convert_and_validate.py
python scripts/run_clinical_scenarios.py
python -m pytest
python scripts/generate_pitch_visuals.py
python scripts/run_backend_e2e_demo.py
python -m uvicorn aahar_backend.api:app --app-dir src --port 8000
```

---

## Clinical Data & Rule Architecture (Member 2 Deliverables)

### 8 Core Drug Classes Covered:
1. **Thyroid Hormone:** Levothyroxine *(Conflict: Milk, Curd, Soy, Morning Chai)*
2. **Hematinics (Iron):** Ferrous Ascorbate / Sulphate *(Conflict: Masala Chai, Filter Coffee, Palak)*
3. **Fluoroquinolone Antibiotics:** Ciprofloxacin / Levofloxacin *(Conflict: Milk, Chaas, Curd, Paneer)*
4. **Anticoagulants:** Warfarin / Acenocoumarol *(Conflict: Sarson ka Saag, Palak, Methi, Green Chutney)*
5. **Calcium Channel Blockers:** Amlodipine *(Conflict: Mosambi Juice, Pomelo/Grapefruit)*
6. **Biguanides (Diabetes):** Metformin *(Conflict: High Glycemic Sugars, Empty Stomach)*
7. **ACE Inhibitors / ARBs:** Telmisartan / Enalapril *(Conflict: Low-Sodium K-Salts, Excessive Coconut Water)*
8. **Statins (Lipid Lowering):** Atorvastatin *(Conflict: Citrus juices, Re-heated trans fats)*

### Data Sources:
- **Food Composition:** ICMR–NIN *Indian Food Composition Tables (IFCT 2017)*
- **Pharmacokinetics & Drug Labels:** US-FDA Drug Label API & DrugBank Monographs
- **Clinical Governance:** Verified by registered clinical nutritionists and physicians.
