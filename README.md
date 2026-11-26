# Aahar-Rx

> **Food-Drug Interaction & Safe Time-Gap Guidance System**  
> *Target: ANVESHAN 2026 (Medical & Health Sciences Track)*  
> *Compliance: Strict Anonymity (Rule 3) & DPDP Act 2023 Guidelines*
>
> **Clinical Safety Notice:** Aahar-Rx provides timing and dietary guidance only. It never advises skipping, altering, or replacing prescribed medication dosages. Consult your doctor or pharmacist before making any change to your treatment plan.

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
│   ├── clinical_rules.csv           # Tabular dataset for clinical review (Member 2)
│   ├── indian_brand_to_salt.json    # Indian brand-to-salt lookup directory (Member 1)
│   └── indian_food_taxonomy.json    # IFCT-aligned Indian food & interferent taxonomy (Member 1)
├── docs/
│   ├── doctor_review_packet.md      # Clinical review summary & physician sign-off (Member 2)
│   ├── pitch_slides_and_defense.md  # Clinical methodology & defense notes (Member 2)
│   └── member1_pitch_slides.md      # Smart Scan pitch slides & stage demo checklist (Member 1)
├── reports/
│   ├── smart_scan_accuracy_report.md
│   ├── benchmark_results.json
│   ├── before_after_strip_recovery.png
│   └── meal_confirmation_flow_visual.png
├── schemas/
│   └── salt_food_schema.json        # Shared Draft 2020-12 contract (Member 1 -> Member 2/4)
├── scripts/
│   ├── convert_and_validate.py      # CSV to JSON schema validator & converter (Member 2)
│   ├── run_clinical_scenarios.py    # Clinical scenario validator (Member 2)
│   ├── test_conflict_engine.py      # Reference conflict & timetable prototype (Member 2)
│   ├── run_benchmarks_and_assets.py # Day 1-6 OCR/Scan benchmark & visual generator (Member 1)
│   └── demo_rehearsal.py            # Day 7 Smart Scan live demo rehearsal runner (Member 1)
├── src/aahar_scan/                  # AI & Smart Scan Python package (Member 1)
└── tests/                           # Automated CV, OCR, Vision, Confirmation & Member 2 tests
```

---

## Smart Scan Architecture (Member 1 Deliverables)

| Module | Path | Responsibility |
| --- | --- | --- |
| **Shared Schema** | [salt_food_schema.json](schemas/salt_food_schema.json) | Draft 2020-12 JSON Schema for Member 1 → Member 2/4 handoff (`ConfirmedScanBundle`) |
| **Brand-to-Salt Directory** | [indian_brand_to_salt.json](data/indian_brand_to_salt.json) | 48 Indian brands across 11 drug classes, OCR noise aliases, strengths & regional brands |
| **Indian Food Taxonomy** | [indian_food_taxonomy.json](data/indian_food_taxonomy.json) | ICMR-NIN IFCT-aligned dishes mapped to interacting nutrients & Member 2 culprit labels |
| **OpenCV Quality & Recovery** | [preprocessing.py](src/aahar_scan/preprocessing.py) | Blur/glare/light/contrast checks with retry tips + glare suppression, curved-foil flattening, CLAHE & rotation recovery |
| **Multi-Engine Strip OCR** | [ocr_engines.py](src/aahar_scan/ocr_engines.py) | `RapidOcrEngine` (PaddleOCR PP-OCRv4 ONNX in-memory), `WindowsNativeOcrEngine`, and optional `TesseractOcrEngine` |
| **Salt Lookup & Fallback** | [salt_resolver.py](src/aahar_scan/salt_resolver.py) | Glued-token splitting, OCR digit/letter correction (`0↔O`, `1↔I`), fuzzy matching, and manual brand/salt search |
| **Meal Vision & Confirmation** | [meal_vision.py](src/aahar_scan/meal_vision.py) | `gemini-2.5-flash` structured JSON meal vision (with offline plate heuristic fallback) + mandatory `MealConfirmationManager` |
| **Pipeline & Member 2 Handoff** | [pipeline.py](src/aahar_scan/pipeline.py), [member2_handoff.py](src/aahar_scan/member2_handoff.py) | Ephemeral DPDP pre-scan consent check + schema-validated bundle export tested against `verified_rules.json` |

### Quickstart (Member 1 Smart Scan)

```powershell
python -m pip install -r requirements.txt
# Optional: enable live Gemini 2.5 Flash Meal Vision
$env:GEMINI_API_KEY="your-api-key"

python -m pytest
python scripts/run_benchmarks_and_assets.py
python scripts/demo_rehearsal.py
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

### Validate Clinical Rules:
```bash
python scripts/convert_and_validate.py
```
This reads `data/clinical_rules.csv`, validates all required schema fields, ranges, and citations, and regenerates `data/verified_rules.json`.
