-- =============================================================================
-- Aahar-Rx v1 Relational Database Schema (Supabase / PostgreSQL)
-- Member 4 (Backend, Safety & Pitch) - Day 1 & Day 4 Deliverable
-- Compliance: DPDP Act 2023 (Consent Logging, Ephemeral Retention, Zero Raw Images)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Pseudonymous Users (zero PII required for ANVESHAN blind review & DPDP minimization)
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'hi', 'mr')),
    age_band TEXT DEFAULT 'adult',
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    erased_at_utc TIMESTAMPTZ NULL
);

-- 2. DPDP Act 2023 Explicit Consent Ledger
CREATE TABLE IF NOT EXISTS consent_logs (
    consent_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    consented BOOLEAN NOT NULL,
    purpose TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT 'minimal_metadata_no_raw_images'
        CHECK (retention_policy IN ('minimal_metadata_no_raw_images', 'ephemeral_session_only')),
    raw_images_stored BOOLEAN NOT NULL DEFAULT FALSE CHECK (raw_images_stored = FALSE),
    granted_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    withdrawn_at_utc TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_consent_logs_user_active
    ON consent_logs(user_id, consented, withdrawn_at_utc);

-- 3. Canonical Active Pharmaceutical Salts
CREATE TABLE IF NOT EXISTS salts (
    salt_id TEXT PRIMARY KEY,
    salt_name TEXT NOT NULL UNIQUE,
    drug_class TEXT NOT NULL,
    rule_ids JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- 4. Indian Foods & IFCT 2017 Nutrient Markers
CREATE TABLE IF NOT EXISTS foods (
    food_id TEXT PRIMARY KEY,
    food_name TEXT NOT NULL UNIQUE,
    ifct_code TEXT NULL,
    primary_nutrients JSONB NOT NULL DEFAULT '[]'::jsonb,
    clinical_note TEXT NULL
);

-- 5. Doctor-Verified Clinical Interaction Rules (seeded from Member 2 data/verified_rules.json)
CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,
    drug_class TEXT NOT NULL,
    active_salts JSONB NOT NULL,
    interfering_nutrients JSONB NOT NULL,
    culprit_indian_foods JSONB NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('HIGH', 'MODERATE', 'LOW')),
    interaction_type TEXT NOT NULL,
    biochemical_mechanism TEXT NOT NULL,
    ifct_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    before_food_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    after_food_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    bioavailability_drop_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    t_max_delay_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ghar_ki_rasoi_swaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    clinical_sign_off JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rules_salts_gin ON rules USING GIN (active_salts);
CREATE INDEX IF NOT EXISTS idx_rules_foods_gin ON rules USING GIN (culprit_indian_foods);

-- 6. Ingested Scan Metadata from Member 1 (STRICTLY NO RAW IMAGE BLOBS)
CREATE TABLE IF NOT EXISTS scan_records (
    scan_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    consent_id TEXT NOT NULL REFERENCES consent_logs(consent_id),
    active_salts JSONB NOT NULL,
    confirmed_foods JSONB NOT NULL,
    nutrient_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    meal_slot TEXT NOT NULL,
    confirmed_by_user BOOLEAN NOT NULL CHECK (confirmed_by_user = TRUE),
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Generated Safe Time-Gap Timetables & QR Health Pass Payloads
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    consent_id TEXT NOT NULL REFERENCES consent_logs(consent_id),
    medications JSONB NOT NULL,
    meals JSONB NOT NULL,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    timetable_slots JSONB NOT NULL,
    qr_health_pass JSONB NOT NULL,
    safety_disclaimer TEXT NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Supabase Row-Level Security (RLS) Readiness
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
