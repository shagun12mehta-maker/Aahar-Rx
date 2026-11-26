# Aahar-Rx Day 6 Live End-to-End Demo Script (Lead Presenter)

> **Target Duration:** 4–5 Minutes | **ANVESHAN Rule 3 Compliant (No names/institutions)**

## Scene 1 — Privacy First (DPDP Act 2023 Gate) — 45s
- **Action:** Show `POST /api/v1/users` + `POST /api/v1/consent`. First demonstrate what happens if a user declines consent (`consented=false` -> `HTTP 403 Forbidden`). Then capture explicit consent (`dpdp_*`).
- **Narration:** *"Before any prescription or meal information touches our backend, Aahar-Rx records explicit DPDP Act 2023 consent. Raw strip and meal photos are never stored—only verified salt and confirmed food names enter the database."*

## Scene 2 — Morning Thyroid & Chai Conflict (`/check-conflict`) — 60s
- **Action:** Submit `Levothyroxine Sodium` at `07:00` with `Morning Masala Chai with Milk` to `POST /api/v1/check-conflict`.
- **Highlight on Screen:**
  - `severity: HIGH` (`RULE-THY-001`)
  - **ICMR-NIN IFCT 2017 Evidence:** Buffalo Milk `210 mg/100g` Calcium, Brewed Chai `105 mg GAE/100ml` Polyphenols
  - **Bioavailability Drop:** `38%` loss (`absorption_curve` array rendered by Member 3's chart)
  - **Ghar-Ki-Rasoi Swap:** Lukewarm lemon water on waking; defer milky chai by 60 minutes.

## Scene 3 — Multi-Drug Daily Safe Timetable & QR Health Pass (`/generate-timetable`) — 75s
- **Action:** Run `POST /api/v1/generate-timetable` for a realistic polypharmacy Indian routine:
  - `Thyronorm (Levothyroxine Sodium)` at `07:00` vs `early_morning_empty_stomach` Chai at `07:15`
  - `Orofer XT (Ferrous Ascorbate)` at `13:15` vs `lunch` (`Palak Paneer`, `Masala Chai`) at `13:00`
  - `Glycomet (Metformin Hydrochloride)` at `20:00` vs `dinner` (`Gulab Jamun`, `Dal-Roti`) at `20:30`
- **Highlight on Screen:**
  - Morning chai automatically shifted to `08:00` (`+45 min` safe gap)
  - Iron tablet shifted to `15:00` (`2.0h` after lunch) with `Nimbu Pani / Amla Juice` swap
  - Metformin scheduled at `20:36` (`take_with_meal_buffer`) to prevent empty-stomach GI irritation
  - **1-Click QR Health Pass** payload fetched from `GET /api/v1/health-pass/{schedule_id}` (zero PII).

## Scene 4 — Clinical Safety & Right to Erasure — 30s
- **Action:** Point out the `safety_disclaimer` embedded on every response and demonstrate `DELETE /api/v1/users/{user_id}/data` clearing stored scans and schedules cleanly.
- **Closing Line:** *"Aahar-Rx never alters a single prescribed dosage—it unlocks full therapeutic efficacy using timing intelligence and kitchen swaps grounded in Indian food science."*
