# Aahar-Rx Member 3 (App, UX & Language) — Wireframes, Accessibility Audit & Pitch Slides

> Target: ANVESHAN 2026 | Strict Blind Review (Rule 3 Compliant)  
> Clinical Notice: Timing and dietary guidance only. Never alters or replaces physician-prescribed dosages.

## Day 1 — Six Core Screen & Consult Flow Architecture

```text
[1. Scan] ---> [2. Confirm + Expiry/Count] ---> [3. Timetable + Auto-Alarms] ---> [4. Absorption Curve] ---> [5. QR Health Pass] ---> [6. Digital Medicine Box]
  |                      |                                   |                             |                         |                         |
  DPDP Consent     Quality Retry Gate            24h Bar + Late-Breakfast Shift    Chart.js 12h Curve       ISO 18004 SVG QR       Stock -1 + 3-Day Alert
  Preset / Upload  Milk Toggle + Box Fallback    High-Risk "Consult Doctor Now"    70% Floor / 115% Limit   Download SVG / Print     1mg / PharmEasy Reorder
```

## Day 5 — Elderly Accessibility Audit Checklist

| Criterion | Implementation Verified | Verification Status |
| --- | --- | --- |
| Minimum body size & toggle | `15px` standard -> `18px` one-tap `Large print` (`.elderly-mode`) toggle in left rail | Verified in `tokens.css` & headless browser |
| Touch target height | Standard controls `40px`, `.elderly-mode` controls & mobile bottom nav `>= 48px`–`52px` | Verified in `app.css` |
| Contrast ratio (`WCAG AA/AAA`) | `#1f1b16` on `#fdfbf7` (`>= 12:1`), `#ffffff` on `#166534` (`>= 6.5:1`), `#534a40` on `#fdfbf7` (`>= 7:1`) | Verified mathematically in `pytest` |
| Vernacular medical clarity | Full UI + audio scripts in English (`en-IN`), Hindi (`hi-IN`), and Marathi (`mr-IN`), calm `-12%` rate | Verified (`30` synthesized MP3 clips) |
| Zero-hassle doctor/family share | Keyboard shortcuts `1`–`6`, High-Risk separate-consent Doctor Consult pop-up, 1-tap QR Health Pass & 1mg/PharmEasy refill | Verified in `Screens.js` & `MedicineBoxScreen.js` |

## Day 6 — Pitch Deck Slides (Visual Proof References)

### Slide A — Patient-First Trilingual React PWA (`en` / `हिन्दी` / `मराठी`)
- Instant single-click switch between English, Hindi Devanagari, and Marathi Devanagari scripts across all 6 screens without reloading or losing scan state.
- Built around an unhurried Warm Apothecary palette crafted via the `heydamir/unslop` nine-pass system—eliminating neon SaaS clutter so senior citizens focus clearly on dose windows (`07:00 | 1.0h before`).
- Live Screenshot: `reports/screenshots/01_scan_en_desktop.png`, `reports/screenshots/03_timetable_hi_elderly.png`.

### Slide B — Pharmacokinetic Visual Absorption Curve & Smart Pill-Meal Scheduler
- Translates every `bioavailability_drop_pct` and `t_max_delay_hours` figure from Member 2's verified JSON directly into a Chart.js 4 12-hour concentration comparison (`Normal baseline 100%` vs `Food-interfered curve`), alongside a **Smart Daily Timeline** that automatically shifts pill/gap alarms when breakfast runs late (`+45m`).
- Live Screenshot: `reports/screenshots/04_absorption_curve_desktop.png`.

### Slide C — Consult Doctor Now (High-Risk Clash Pop-Up), Digital Medicine Box & 1-Click QR Pass
- Genuine `HIGH` severity interactions immediately present **Consult Doctor Now (Video Call)** with separate DPDP consent and a pre-loaded anonymous **Clinician Clash Report View** (clarifying only a licensed doctor adjusts doses).
- Scanned strip expiry dates and tablet counts feed the **Digital Medicine Box**, tracking taken doses (`-1 tablet`), flagging `<= 3 days` stock, and offering 1-click search links to **1mg** & **PharmEasy**, backed by `30` synthesized EN/HI/MR elderly voice clips (`ALERT-HIGH-RISK`, `ALERT-REFILL`, and all `8` rules).
- Live Screenshot: `reports/screenshots/05_qr_pass_mr_desktop.png`, `reports/screenshots/07_consult_doctor_popup.png`, `reports/screenshots/08_medicine_box_desktop.png`, `reports/screenshots/06_scan_mobile_390.png`.
