# Aahar-Rx

> **Food-Drug Interaction & Safe Time-Gap Guidance System**  
> *Target: ANVESHAN 2026 (Medical & Health Sciences Track)*  
> *Compliance: Strict Anonymity (Rule 3) & DPDP Act 2023 Guidelines*

---

## Overview
Aahar-Rx bridges clinical pharmacology with authentic Indian dietary practices. In India, polypharmacy patients frequently suffer from therapeutic failure or toxicity due to unaddressed drug-nutrient interactions (e.g., taking Levothyroxine with milky masala tea, or taking Iron supplements with polyphenol-rich meals).

Aahar-Rx detects these conflicts through medicine strip OCR and meal photo analysis, calculates evidence-backed **Safe Time Gaps**, and offers **"Ghar-Ki-Rasoi"** practical kitchen swaps without altering physician-prescribed dosages.

---

## Repository Structure

```text
aveshan2/
├── data/
│   ├── verified_rules.json     # Primary clinical rules dataset consumed by Backend & UI
│   └── clinical_rules.csv      # Tabular dataset for clinical review & editing
├── docs/
│   ├── doctor_review_packet.md # Clinical review summary & physician sign-off document
│   └── pitch_slides_and_defense.md # Methodology & presentation defense notes
├── scripts/
│   └── convert_and_validate.py # CSV to JSON schema validator & converter
└── README.md
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

---

## Getting Started

### Validate Clinical Rules:
```bash
python scripts/convert_and_validate.py
```
This reads `data/clinical_rules.csv`, validates all required schema fields, ranges, and citations, and regenerates `data/verified_rules.json`.
