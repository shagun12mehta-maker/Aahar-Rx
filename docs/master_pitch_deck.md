# Aahar-Rx Master Pitch Deck (ANVESHAN 2026)

> **Strict Anonymity Compliance (ANVESHAN Rule 3):** Zero student names, mentor names, or university/institution names or logos appear in this deck.

---

## Slide 1 — Title & Mission
- **Title:** **Aahar-Rx: Food-Drug Interaction & Safe Time-Gap Guidance for Indian Kitchens**
- **One-Liner:** Bridging clinical pharmacology with authentic Indian meals—without altering prescribed medication dosages.

## Slide 2 — Problem & Clinical Objectives
- **The Silent Failure Mode:** Polypharmacy patients take medicines dutifully, yet Indian dietary staples (*milky masala chai, dahi, chaas, palak paneer, sarson ka saag, sendha namak, coconut water*) chelate or antagonize active drugs in the gut.
- **Core Objectives:**
  1. Scan physical medicine strips and Indian meals quickly in English, Hindi, and Marathi (Member 1 & 3).
  2. Evaluate conflicts deterministically using doctor-verified **ICMR-NIN IFCT 2017** and **OpenFDA/DrugBank** monographs (Member 2).
  3. Compute conflict-free **Safe Time-Gap Timetables**, visual **Pharmacokinetic Absorption Curves**, and **Ghar-Ki-Rasoi** kitchen swaps while upholding **DPDP Act 2023** privacy (Member 4).

## Slide 3 — System Architecture (End-to-End 4-Module Pipeline)
- Visual: `reports/system_architecture_and_dpdp.png`
- **Frontend (Member 3):** Elderly-friendly PWA, Recharts Absorption Curve, Multilingual Voice (EN/HI/MR), 1-Click QR Health Pass.
- **AI Scan (Member 1):** Strip OCR + Gemini Vision + mandatory user confirmation before clinical lookup.
- **Backend & Safety (Member 4):** FastAPI REST API + PostgreSQL/Supabase schema (`users`, `salts`, `foods`, `rules`, `schedules`, `consent_logs`) + DPDP consent/erasure gates.
- **Clinical Rules (Member 2):** Immutable `verified_rules.json` covering 8 high-impact drug classes.

## Slide 4 — Major Findings & Pharmacokinetic Impact
- Visual: `reports/absorption_curve_and_timetable.png`
- **Key Findings from Verified Dataset (`verified_rules.json`):**
  - **Levothyroxine + Buffalo Milk Chai:** `38%` bioavailability drop (`+1.5h` $T_{\max}$ delay) from `210 mg/100g` Ca and `105 mg GAE/100ml` polyphenols (`RULE-THY-001`).
  - **Iron (Ferrous Ascorbate) + Tea / Palak Paneer:** `62%` absorption loss (`+2.0h` $T_{\max}$ delay); Nimbu Pani / Amla Vitamin-C swap restores soluble $\text{Fe}^{2+}$ uptake (`RULE-IRO-002`).
  - **Ciprofloxacin + Chaas / Dahi / Paneer:** `52%` peak drop via divalent cation chelation (`RULE-ANT-003`).
  - **Warfarin + Sarson ka Saag / Coriander Chutney:** Vitamin K1 (`380–483 mcg/100g`) antagonizes VKORC1, collapsing INR (`RULE-BLD-004`).
  - **Amlodipine / Statins + Chakotra / Mosambi:** CYP3A4 inhibition elevates drug exposure (`+30%` to `+45%` AUC, `RULE-HTN-005` & `RULE-LIP-008`).

## Slide 5 — DPDP Act 2023 Privacy & Clinical Safety Architecture
- **Explicit Consent First:** Backend blocks `/check-conflict`, `/generate-timetable`, and `/scans/ingest` with `HTTP 403` unless active consent is logged in `consent_logs`.
- **Zero Raw Image Persistence:** Request schemas explicitly forbid raw image/base64 payloads (`HTTP 422`), and SQL `CHECK (raw_images_stored = FALSE)` guarantees zero photo retention.
- **Right to Erasure:** Single API call (`DELETE /api/v1/users/{id}/data`) wipes scan metadata and schedules and withdraws consent.
- **Clinical Liability Guardrail:** Timing & dietary guidance only—never skips, stops, or alters prescribed doses.

## Slide 6 — Cost-Effectiveness & Accessibility
- **Zero Expensive Hardware:** Works on entry-level Android smartphones via lightweight PWA + QR Health Pass (offline printable/shareable card for family caregivers & rural ASHA workers).
- **Low Cloud Inference Footprint:** Deterministic rule engine runs in `<5 ms` locally/PostgreSQL with zero per-query LLM cost for clinical decisions.
- **Vernacular Voice & Elderly UX:** Large high-contrast UI + Hindi/Marathi/English voice cues eliminate literacy barriers.

## Slide 7 — Commercialisation & Scaling Roadmap
- **Phase 1 (B2C & Caregiver Freemium):** Chronic-care polypharmacy companion (Thyroid, Diabetes, Cardiac, Antenatal Anemia) + Pharmacy QR slip integration.
- **Phase 2 (B2B Clinics & Pharmacy Chains):** White-label API integration for e-prescriptions, diagnostic labs, and hospital discharge summaries (ABDM/HIPAA-aligned audit trail).
- **Scalability:** Decoupling brand names -> active chemical salts lets Member 2's CSV-to-JSON validator expand from 8 to 100+ drug classes in minutes without backend code changes.
