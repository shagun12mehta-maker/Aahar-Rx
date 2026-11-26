# Aahar-Rx Member 3 (App, UX & Language) — Wireframes, Accessibility Audit & Pitch Slides

> Target: ANVESHAN 2026 | Strict Blind Review (Rule 3 Compliant)  
> Clinical Notice: Timing and dietary guidance only. Never alters or replaces physician-prescribed dosages.

## Day 1 — Five Core Screen Wireframe Architecture

```text
[1. Scan] ---> [2. Confirm] ---> [3. Timetable + Voice] ---> [4. Absorption Curve] ---> [5. QR Health Pass]
  |                |                        |                          |                        |
  DPDP Consent     Quality Retry Gate       24h Visual Timeline        Chart.js 12h Curve       ISO 18004 SVG QR
  Preset / Upload  Toggle Milk in Chai      "Ghar-Ki-Rasoi" Swaps      70% Therapeutic Floor    Download SVG / Print
  Manual Search    Add/Remove Dish          EN / HI / MR MP3 Voice     115% Safety Ceiling      One-Tap Voice Read
```

## Day 5 — Elderly Accessibility Audit Checklist

| Criterion | Implementation Verified | Verification Status |
| --- | --- | --- |
| Minimum body size & toggle | `15px` standard -> `18px` one-tap `Large print` (`.elderly-mode`) toggle in left rail | Verified in `tokens.css` & headless browser |
| Touch target height | Standard controls `40px`, `.elderly-mode` controls & mobile bottom nav `>= 48px`–`52px` | Verified in `app.css` |
| Contrast ratio (`WCAG AA/AAA`) | `#1f1b16` on `#fdfbf7` (`>= 12:1`), `#ffffff` on `#166534` (`>= 6.5:1`), `#534a40` on `#fdfbf7` (`>= 7:1`) | Verified mathematically in `pytest` |
| Vernacular medical clarity | Full UI + audio scripts in English (`en-IN`), Hindi (`hi-IN`), and Marathi (`mr-IN`), calm `-12%` rate | Verified (`24` synthesized MP3 clips) |
| Zero-hassle doctor/family share | Keyboard shortcut `5` or single-tap `QR health pass` with SVG export and print stylesheet | Verified in `Screens.js` & `app.css` |

## Day 6 — Pitch Deck Slides (Visual Proof References)

### Slide A — Patient-First Trilingual React PWA (`en` / `हिन्दी` / `मराठी`)
- Instant single-click switch between English, Hindi Devanagari, and Marathi Devanagari scripts without reloading or losing scan state.
- Built around an unhurried Warm Apothecary palette crafted via the `heydamir/unslop` nine-pass system—eliminating neon SaaS clutter so senior citizens focus clearly on dose windows (`07:00 | 1.0h before`).
- Live Screenshot: `reports/screenshots/01_scan_en_desktop.png`, `reports/screenshots/03_timetable_hi_elderly.png`.

### Slide B — Pharmacokinetic Visual Absorption Curve (Member 2 Data -> Live Chart)
- Translates every `bioavailability_drop_pct` and `t_max_delay_hours` figure from Member 2's verified JSON directly into a Chart.js 4 12-hour concentration comparison (`Normal baseline 100%` vs `Food-interfered curve`).
- Covers both chelation drops (e.g., Levothyroxine `-38%`, Ferrous Ascorbate `-62%`, Ciprofloxacin `-52%`) and CYP3A4 enzymatic spikes above the `115%` ceiling (e.g., Amlodipine `+45%` with Mosambi/Pomelo).
- Live Screenshot: `reports/screenshots/04_absorption_curve_desktop.png`.

### Slide C — Elderly Voice Reminders & 1-Click Offline QR Health Pass
- Pre-synthesized Indian neural voices (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`, `mr-IN-AarohiNeural`) paired with Web Speech synthesis fallback explain safe time windows and `"Ghar-Ki-Rasoi"` kitchen swaps aloud.
- **1-Click QR Health Pass** encodes strictly minimal timing & swap JSON into an offline-scannable ISO 18004 QR SVG card (with zero raw patient photos stored, honoring DPDP Act 2023).
- Live Screenshot: `reports/screenshots/05_qr_pass_mr_desktop.png`, `reports/screenshots/06_scan_mobile_390.png`.
