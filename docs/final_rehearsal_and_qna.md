# Aahar-Rx: Day 7 Podium Defense & Jury Q&A Rehearsal
**Target:** ANVESHAN 2026 Presentation & Poster Defense  
**Speaker / Defense Lead:** Member 2 (Clinical Rules & Data)  
**Tone:** Authoritative, scientifically rigorous, concise, and clinically compliant.

---

## 1. Top 5 Killer Questions from Medical & Technical Judges

### Q1: "Why did you build a fixed rule engine instead of asking a Large Language Model (like GPT-4 or Gemini) to give dietary advice?"
**Your Winning Answer:**
> *"In clinical medicine, non-deterministic generative models present two severe risks: **hallucinations** and **inconsistency across patient queries**. An LLM might recommend taking a pill with milk in one session and warn against it in another. At Aahar-Rx, our AI Vision (Member 1) only performs image recognition. The moment the medicine salt and food are detected, our clinical engine runs on an **immutable, deterministic ruleset backed by ICMR-NIN IFCT (2017) and FDA bioavailability curves**. Every output is 100% reproducible, auditable, and doctor-signed."*

### Q2: "Can you explain the exact biochemical mechanism of how tea inhibits iron absorption, and why your swap works?"
**Your Winning Answer:**
> *"Certainly. Brewed Indian black tea contains approximately $105\,\text{mg}$ gallotannins and polyphenols per $100\,\text{ml}$. In the neutral-to-alkaline milieu of the duodenum, these polyphenols bind to non-heme ferric ($\text{Fe}^{3+}$) ions, forming high-molecular-weight insoluble iron-tannate precipitates. These complexes are completely impermeable to the apical Divalent Metal Transporter 1 (DMT-1) on duodenal enterocytes, dropping absorption by up to 60–70%. Our 'Ghar-Ki-Rasoi' swap recommends **Nimbu Pani or Amla juice**: ascorbic acid acts as an electron donor, reducing $\text{Fe}^{3+}$ into soluble $\text{Fe}^{2+}$ and chelating it in an acidic matrix that DMT-1 can readily transport—boosting uptake up to 300%."*

### Q3: "What if your app gives wrong advice and a patient skips their medicine? What is your legal and clinical liability?"
**Your Winning Answer:**
> *"Aahar-Rx is engineered under strict clinical safety boundaries: **the system never advises skipping, stopping, or altering prescribed medication dosages**. Our guidance is strictly confined to educational dietary timing intervals (Safe Time Gaps) and kitchen substitutions. Furthermore, under the Digital Personal Data Protection (DPDP) Act 2023, explicit user consent is captured prior to image processing, and a prominent clinical disclaimer is rendered across every screen confirming that Aahar-Rx supplements, but does not replace, primary physician consultations."*

### Q4: "How did you validate your nutrient numbers against actual Indian diets?"
**Your Winning Answer:**
> *"We utilized the National Institute of Nutrition's (ICMR-NIN) gold-standard **Indian Food Composition Tables (IFCT 2017)**. For example, rather than using generic Western milk data, we utilized Table D for buffalo milk ($210\,\text{mg}$ calcium per $100\,\text{g}$) and cow milk ($118\,\text{mg}/100\,\text{g}$). For green leafy vegetables, we utilized Table A values for palak ($483\,\mu\text{g}$ Vitamin K1) and sarson ka saag ($380\,\mu\text{g}$), which explain why North Indian winter diets cause acute Warfarin instability."*

### Q5: "How will you scale this from 8 drug classes to hundreds of drugs in the market?"
**Your Winning Answer:**
> *"Our architecture decouples active salts from commercial brand names. India has over 100,000 brand names, but they map down to a finite set of chemical active pharmaceutical ingredients (APIs). Member 1’s OCR maps commercial brand names to active salts, which immediately inherit our core pharmacokinetic rules. Expanding from 8 to 80 drug classes simply requires populating our validated CSV schema, which our automated Python pipeline validates and converts into production JSON in seconds."*

---

## 2. Competition Rule 3 (Blind Review) Checklist for Member 2:
- [x] No personal student names on slides, posters, or code comments.
- [x] No college / university names, logos, or department watermarks.
- [x] No mentor or faculty guide names visible in documentation or UI screenshots.
- [x] Focus purely on scientific rigor, engineering elegance, and clinical impact.
