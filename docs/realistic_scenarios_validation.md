# Aahar-Rx: Realistic Indian Patient Meal-Medicine Scenarios & Validation
**Lead:** Member 2 (Clinical Rules & Data)  
**Target:** Day 5 Scenario Verification for ANVESHAN 2026

---

## Scenario 1: The Morning Thyroid Dilemma (Hypothyroidism)
* **Patient Persona:** Mrs. Sharma (Age 52), diagnosed with primary hypothyroidism.
* **Prescription:** Tablet Levothyroxine Sodium 75 mcg, daily morning.
* **Daily Dietary Routine:** Wakes up at 6:45 AM, immediately drinks a large cup of whole buffalo milk masala tea (Chai) with 2 Marie biscuits at 7:00 AM, swallowing the pill with the tea.
* **Clinical Hazard Detected:**
  - Buffalo milk supplies **210 mg Calcium / 100g**; black tea extracts supply **105 mg Tannins / 100ml**.
  - Polyvalent $\text{Ca}^{2+}$ cations bind to the phenolic and carboxylate groups of Levothyroxine, forming an insoluble chelate matrix in the proximal duodenum.
  - Estimated bioavailability loss: **~38%**. Patient's serum TSH remains elevated (8.5 mIU/L) despite regular medication intake.
* **Aahar-Rx Engine Resolution:**
  - **Conflict Severity:** HIGH.
  - **Actionable Safe Schedule:** Take Levothyroxine at 6:30 AM with 200ml plain lukewarm water. Defer morning chai until 7:30 AM (minimum 60-minute window).
  - **"Ghar-Ki-Rasoi" Swap:** Morning lukewarm water with a squeeze of fresh lemon (acidic gastric buffer).

---

## Scenario 2: The Anemic Antenatal Mother (Iron Deficiency)
* **Patient Persona:** Priya (Age 26), 2nd trimester of pregnancy, Hb: 9.2 g/dL.
* **Prescription:** Tablet Ferrous Ascorbate 100 mg (equivalent to elemental iron) + Folic Acid.
* **Daily Dietary Routine:** Consumes lunch consisting of Palak Paneer with whole wheat rotis, followed immediately by hot masala chai or South Indian filter coffee.
* **Clinical Hazard Detected:**
  - Palak supplies **658 mg Oxalates / 100g**; Paneer supplies **480 mg Calcium / 100g**; Chai delivers high polyphenolic tannins.
  - Calcium and iron compete directly for the Divalent Metal Transporter 1 (DMT-1) at the enterocyte apical membrane. Tannins precipitate iron into insoluble iron-tannate complexes.
  - Elemental iron bioavailability drops by **62%**.
* **Aahar-Rx Engine Resolution:**
  - **Conflict Severity:** HIGH.
  - **Actionable Safe Schedule:** Take Iron supplement 1 hour before lunch or 2 hours after lunch.
  - **"Ghar-Ki-Rasoi" Swap:** Replace post-lunch tea with freshly prepared **Nimbu Pani** or **Amla juice**. Ascorbic acid actively reduces insoluble $\text{Fe}^{3+}$ to soluble $\text{Fe}^{2+}$, tripling duodenal uptake. Swap Palak Paneer to **Palak Corn/Aloo with lemon squeeze**.

---

## Scenario 3: The Summer Coconut Water Rush (Hypertension on ARBs)
* **Patient Persona:** Ramesh (Age 61), essential hypertension, mild borderline eGFR (58 mL/min/1.73m²).
* **Prescription:** Tablet Telmisartan 40 mg once daily.
* **Daily Dietary Routine:** Because of hot summer weather, drinks 3 glasses of tender coconut water throughout the day and seasons meals with Sendha Namak (marketed as "heart-healthy low-sodium salt").
* **Clinical Hazard Detected:**
  - Tender coconut water supplies **250 mg Potassium / 100ml** (3 glasses $\approx 1800$ mg $\text{K}^{+}$); Sendha Namak (KCl based) supplies **12,500 mg $\text{K}^{+}$ / 100g**.
  - Telmisartan blocks Angiotensin II Type 1 ($AT_1$) receptors, reducing aldosterone secretion and impairing distal renal potassium excretion.
  - Combined effect produces hyperkalemia (serum potassium $> 5.6$ mEq/L), escalating risk of cardiac conduction abnormalities and fatal arrhythmias.
* **Aahar-Rx Engine Resolution:**
  - **Conflict Severity:** MODERATE-HIGH.
  - **Actionable Safe Schedule:** Limit coconut water to maximum 1 glass per day spaced 3+ hours away from Telmisartan dose.
  - **"Ghar-Ki-Rasoi" Swap:** Replace Sendha Namak with regular iodized salt strictly limited to $< 4$g/day, enhancing flavor with Amchur and roasted cumin. Replace excess coconut water with spiced diluted chaas (without added salt).

---

## Scenario 4: The Winter Saag Feasting (Patient on Anticoagulants)
* **Patient Persona:** Gurpreet (Age 68), deep vein thrombosis (DVT) post-orthopedic surgery.
* **Prescription:** Tablet Warfarin Sodium 5 mg, titrated to target INR 2.0–3.0.
* **Daily Dietary Routine:** During winter, consumes large portions of Sarson ka Saag with Makki ki Roti, and thick coriander-mint chutney twice daily.
* **Clinical Hazard Detected:**
  - Sarson ka Saag supplies **380 $\mu$g Phylloquinone (Vitamin K1) / 100g**; Coriander chutney supplies **310 $\mu$g / 100g**.
  - Exogenous Vitamin K overcomes the competitive inhibition of Vitamin K Epoxide Reductase (VKORC1), accelerating gamma-carboxylation of clotting factors II, VII, IX, and X.
  - Patient's INR drops from 2.5 to 1.3 within 72 hours, triggering a severe thrombotic crisis.
* **Aahar-Rx Engine Resolution:**
  - **Conflict Severity:** CRITICAL / HIGH.
  - **Actionable Safe Schedule:** Dietary Vitamin K intake must remain strictly consistent day-to-day. Acute boluses of winter saag are flagged immediately.
  - **"Ghar-Ki-Rasoi" Swap:** Lauki (Bottle Gourd) kofta, Torai (Ridge gourd), or Bhindi sabzi (Vitamin K $< 5\,\mu\text{g}/100\text{g}$).
