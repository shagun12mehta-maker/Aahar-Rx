# Aahar-Rx DPDP Act 2023 Privacy Compliance Note (Member 4)

## 1. Scope & Lawful Basis (Explicit Consent)
In accordance with the **Digital Personal Data Protection (DPDP) Act 2023**, Aahar-Rx processes health-adjacent medication and dietary records solely on the basis of **free, specific, informed, unconditional, and unambiguous consent**:

- Before any medication scan ingestion, `/check-conflict`, or `/generate-timetable` request is executed, the backend checks `consent_logs` in the database (`require_active_consent(user_id, consent_id)`).
- Missing, refused (`consented=false`), or withdrawn consent returns **`HTTP 403 Forbidden`** before any clinical evaluation runs.

## 2. Data Minimization & Ephemeral Image Handling
- **Zero Raw Image Storage:** Medicine strip photos and meal photos are processed transiently by Member 1's Smart Scan module and **never** transmitted to or stored by the backend database.
- **Schema-Level Enforcement:** Request models enforce `StrictNoRawImageModel` (`extra="forbid"` plus explicit rejection of `image_base64`, `raw_image`, `raw_image_bytes`, `image_bytes`, `photo_base64`, `prescription_photo`, `meal_photo`). The `consent_logs` table enforces `CHECK (raw_images_stored = FALSE)`.
- **Pseudonymous Profiles:** Users are identified exclusively by random UUID-derived `usr_*` identifiers (`preferred_language` and `age_band` only—no name, phone number, Aadhaar, or email is collected).

## 3. Consent Withdrawal & Right to Erasure
- **Instant Withdrawal:** `POST /api/v1/consent/{consent_id}/withdraw` timestamps `withdrawn_at_utc`, immediately blocking subsequent conflict/timetable calls.
- **Full Erasure:** `DELETE /api/v1/users/{user_id}/data` atomically deletes all `scan_records` and `schedules` rows for that user, withdraws all active consents, and marks the user profile erased.

## 4. Clinical Safety Boundary
Every conflict and timetable payload carries the non-removable **Clinical Safety Disclaimer** clarifying that guidance covers meal-medicine timing and kitchen swaps only, and never advises skipping, altering, or replacing prescribed dosages.
