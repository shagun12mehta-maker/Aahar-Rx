# Aahar-Rx Member 3 — Unslop Design Direction & Nine-Pass Craft Log

> Attribution: Structured UI audit and nine-pass methodology adapted from **unslop** by Damir Sokolovsky (`https://x.com/heydamir`, `https://heydamir.design/unslop`), licensed under CC BY 4.0.  
> Competition Compliance: ANVESHAN 2026 Rule 3 blind-review formatting (zero personal, mentor, or institution names).

## 1. Five-Line Creative Direction

- **Product:** Aahar-Rx helps Indian chronic-care patients time daily medications around meals, inspect bioavailability loss or spikes, and carry a trilingual 1-Click QR Health Pass.
- **Character:** Calm, clinical, attentive, unhurried.
- **World:** Archival apothecary prescription paper paired with terracotta cookware, brass clinical instruments, and botanical herbs.
- **Moments:** (1) The Chart.js 4 **Absorption Curve** comparing baseline plasma availability against food-interfered bioavailability and therapeutic thresholds; (2) the printable **1-Click QR Health Pass** specimen card styled like a real pharmacy intake record.
- **Signature:** A tabular 1px solid dose-timing rule (`HH:MM | Xh before / Yh after`) carried consistently across the top bar, timetable timeline, and QR Health Pass header.

## 2. Anti-Slop Redline Guards Applied

- Eliminated indigo/violet gradients, glassmorphism backdrop blurs, decorative blobs, glowing shadows, gradient text clipping, and `9999px` pill bloat.
- Replaced every decorative emoji across English, Hindi, and Marathi copy with unified `18px` line SVG icons (`stroke-width="1.5"`).
- Removed exclamation marks (`!`), synthetic greeting headings, wide-tracked uppercase nav labels, and AI hype copy.
- Enforced tabular numeric alignment (`tabular-nums`) for all dose timestamps, `-38.0%` bioavailability deltas, `T_max` shifts, and IFCT nutrient figures (`mg / 100g`).

## 3. Nine-Pass Execution Summary

1. **Spacing (`tokens.css`, `app.css`):** Strict `4px` rhythmic scale (`4, 8, 12, 16, 20, 24, 32, 48`), dense `248px` left rail, equal row heights in prescription/dish lists, sticky `52px` bottom bar on mobile (`<= 960px`).
2. **Color:** Warm Apothecary Paper ramp (`#f7f4ee` page, `#fdfbf7` card, `#efe9df` raised input, `#1f1b16` ink) + single botanical accent (`#166534`, `> 7:1` contrast with white text) + restrained semantic tones (`#b42318` high, `#9a4708` moderate).
3. **Icons:** Single coherent inline SVG stroke icon set (`frontend/js/icons.js`) aligned inside fixed `20px` boxes with `8px` label gaps.
4. **Copy:** Verified patient-respectful clinical phrasing across all keys in `en`, `hi`, and `mr` (`frontend/data/i18n.json`), retaining the mandatory timing-only clinical safety notice.
5. **Typography:** `Instrument Sans` paired with Devanagari-clear `Noto Sans Devanagari` / `Nirmala UI` and `IBM Plex Mono` (`400`/`500`/`600` weights only), plus an explicit `.elderly-mode` (`18px` body, `48px` touch targets, darker ink contrast `#14110e`).
6. **Layout:** Asymmetric `1.55fr : 1fr` desktop splits prioritizing the meal confirmation plate, Chart.js curve, and QR Health Pass specimen rather than equal-card SaaS grids.
7. **Details:** Nested radii (`16px` panels, `12px` cards, `8px` controls, `4px` keycaps `1`-`5`), crisp hairline borders (`rgba(31,27,22,0.1)`), and subtle top border accent on the printed QR specimen.
8. **Visuals:** Real quantitative Chart.js 4 curve computed mathematically from `data/verified_rules.json` + crisp ISO 18004 SVG QR encoder (`qrcode-generator`).
9. **Motion:** Single curve `cubic-bezier(0.22, 1, 0.36, 1)` (`150ms` transitions on color/background/border/transform only, subtle `0.98` button press, zero looping pulse animations).
