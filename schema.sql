-- ==============================================================================
-- Aahar-Rx: Food-Drug Interaction & Safe Time-Gap Guidance System
-- Database Schema for Supabase / PostgreSQL
-- Target: ANVESHAN 2026 (Medical & Health Sciences Track)
-- Compliance: DPDP Act 2023 & Strict Anonymity (ANVESHAN Rule 3)
-- Updated: Added Medicine Box, Routine Alarms, and Clash Reports / Doctor Consults
-- ==============================================================================

-- Enable UUID extension for cryptographically secure, anonymous identifiers
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. USERS TABLE
-- Fully anonymized patient / client identity (Zero PII, satisfies ANVESHAN Rule 3)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anonymous_identifier VARCHAR(64) UNIQUE NOT NULL, -- Pseudonymized hash or token
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_anon_id ON users(anonymous_identifier);

-- ------------------------------------------------------------------------------
-- 2. CONSENTS TABLE
-- DPDP Act 2023 Digital Consent Governance
-- Hard gate: Scan, conflict, and doctor-share operations require active consent
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Used directly as consent_id
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose VARCHAR(255) NOT NULL DEFAULT 'CLINICAL_FOOD_DRUG_INTERACTION_ANALYSIS',
    consent_type VARCHAR(100) NOT NULL DEFAULT 'PATIENT_PROCESSING', -- 'PATIENT_PROCESSING' or 'DOCTOR_SHARE'
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    dpdp_version VARCHAR(50) NOT NULL DEFAULT 'DPDP_ACT_2023',
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consents_lookup ON consents(id, status, valid_until);
CREATE INDEX IF NOT EXISTS idx_consents_user ON consents(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_type ON consents(consent_type);

-- ------------------------------------------------------------------------------
-- 3. SALTS TABLE
-- Active Pharmaceutical Ingredients (APIs) and drug classifications
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS salts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL, -- e.g., 'Levothyroxine Sodium', 'Ferrous Ascorbate'
    drug_class VARCHAR(255) NOT NULL,  -- e.g., 'Thyroid Hormone Replacements'
    therapeutic_category VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_salts_name ON salts(name);
CREATE INDEX IF NOT EXISTS idx_salts_drug_class ON salts(drug_class);

-- ------------------------------------------------------------------------------
-- 4. FOODS TABLE
-- Indian Dietary & IFCT (ICMR-NIN) Nutritional Composition
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS foods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL, -- e.g., 'Morning Masala Chai with Milk', 'Dahi / Curd'
    regional_name VARCHAR(255),        -- Hindi / regional vernacular name
    ifct_code VARCHAR(50),             -- ICMR-NIN IFCT 2017 code (e.g. 'D001', 'D002')
    primary_interfering_nutrient VARCHAR(255), -- e.g., 'Calcium', 'Tannins', 'Phytates'
    nutrient_density VARCHAR(100),     -- e.g., '210 mg / 100g'
    category VARCHAR(100),             -- 'Dairy', 'Beverages', 'Leafy Greens', etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_foods_name ON foods(name);
CREATE INDEX IF NOT EXISTS idx_foods_ifct_code ON foods(ifct_code);

-- ------------------------------------------------------------------------------
-- 5. RULES TABLE
-- Clinical Interaction Rules aligned with Member 2's verified_rules.json
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'RULE-THY-001', 'RULE-IRO-002'
    drug_class VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('HIGH', 'MODERATE', 'LOW')),
    interaction_type VARCHAR(255) NOT NULL,
    biochemical_mechanism TEXT NOT NULL,
    
    -- Safe time gaps in hours
    safe_before_food_hours NUMERIC(4, 2) NOT NULL DEFAULT 0.0,
    safe_after_food_hours NUMERIC(4, 2) NOT NULL DEFAULT 0.0,
    
    -- Pharmacokinetic impact metrics
    bioavailability_drop_pct NUMERIC(5, 2),
    t_max_delay_hours NUMERIC(4, 2),
    
    -- Structured Clinical Arrays & Objects matching verified_rules.json
    active_salts JSONB NOT NULL DEFAULT '[]'::jsonb,
    interfering_nutrients JSONB NOT NULL DEFAULT '[]'::jsonb,
    culprit_indian_foods JSONB NOT NULL DEFAULT '[]'::jsonb,
    ifct_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    ghar_ki_rasoi_swaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    clinical_sign_off JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_rule_id ON rules(rule_id);
CREATE INDEX IF NOT EXISTS idx_rules_severity ON rules(severity);
CREATE INDEX IF NOT EXISTS idx_rules_active_salts_gin ON rules USING gin(active_salts);
CREATE INDEX IF NOT EXISTS idx_rules_culprit_foods_gin ON rules USING gin(culprit_indian_foods);

-- ------------------------------------------------------------------------------
-- 6. SCHEDULES TABLE
-- Patient Timetable & Intake Guidance
-- Enforces mandatory clinical disclaimer & consent reference
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_id UUID NOT NULL REFERENCES consents(id) ON DELETE RESTRICT,
    salt_id UUID REFERENCES salts(id) ON DELETE SET NULL,
    rule_id UUID REFERENCES rules(id) ON DELETE SET NULL,
    
    medicine_name VARCHAR(255) NOT NULL,
    prescribed_time TIME NOT NULL,
    meal_name VARCHAR(100),
    planned_meal_time TIME,
    calculated_safe_time TIME NOT NULL,
    
    status VARCHAR(50) NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED', 'TAKEN', 'DEFERRED', 'SKIPPED')),
    clinical_disclaimer TEXT NOT NULL DEFAULT 'Aahar-Rx provides timing and dietary guidance only. The app never advises skipping, altering, or replacing prescribed medication dosages. Any dose or medicine change is made only by a licensed doctor, through the Doctor Video Consult.',
    
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedules_user_date ON schedules(user_id, calculated_safe_time);
CREATE INDEX IF NOT EXISTS idx_schedules_consent ON schedules(consent_id);

-- ------------------------------------------------------------------------------
-- 7. MEDICINE BOX TABLE (NEW MODULE)
-- Stock and Expiry Tracking with 3-Day Low Stock Alerts & Deep-link Reorder
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicine_box (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    expiry_date DATE NOT NULL,
    initial_count INT NOT NULL CHECK (initial_count >= 0),
    remaining_count INT NOT NULL CHECK (remaining_count >= 0),
    daily_dosage_count INT NOT NULL DEFAULT 1 CHECK (daily_dosage_count > 0),
    low_stock_alert BOOLEAN NOT NULL DEFAULT FALSE,
    reorder_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medicine_box_user ON medicine_box(user_id);
CREATE INDEX IF NOT EXISTS idx_medicine_box_low_stock ON medicine_box(user_id, low_stock_alert);

-- ------------------------------------------------------------------------------
-- 8. ALARMS TABLE (NEW MODULE)
-- Routine Shift Engine: Dynamic alarm shift based on meal anchors & delays
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alarms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medicine_name VARCHAR(255) NOT NULL,
    active_salt VARCHAR(255) NOT NULL,
    scheduled_time TIME NOT NULL,
    meal_anchor VARCHAR(100) NOT NULL, -- e.g., 'Breakfast', 'Lunch', 'Morning Chai'
    shifted_time TIME,
    shift_reason TEXT,
    fcm_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alarms_user ON alarms(user_id);
CREATE INDEX IF NOT EXISTS idx_alarms_scheduled ON alarms(user_id, scheduled_time);

-- ------------------------------------------------------------------------------
-- 9. CLASH REPORTS & DOCTOR CONSULT SESSIONS (NEW MODULE)
-- Generates shareable report tokens & Jitsi Meet WebRTC URLs for High-Risk clashes
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clash_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_token VARCHAR(64) UNIQUE NOT NULL,
    doctor_consent_id UUID NOT NULL REFERENCES consents(id) ON DELETE RESTRICT,
    active_salt VARCHAR(255) NOT NULL,
    conflicted_food VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('HIGH', 'MODERATE', 'LOW')),
    biochemical_mechanism TEXT NOT NULL,
    bioavailability_drop_pct NUMERIC(5, 2),
    ghar_ki_rasoi_swap JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clash_reports_token ON clash_reports(report_token);
CREATE INDEX IF NOT EXISTS idx_clash_reports_consent ON clash_reports(doctor_consent_id);

CREATE TABLE IF NOT EXISTS consult_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES clash_reports(id) ON DELETE CASCADE,
    anonymized_doctor_id VARCHAR(64) NOT NULL, -- Anonymized doctor identifier
    jitsi_room_url TEXT NOT NULL,
    session_status VARCHAR(50) NOT NULL DEFAULT 'REQUESTED' CHECK (session_status IN ('REQUESTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consult_sessions_report ON consult_sessions(report_id);
CREATE INDEX IF NOT EXISTS idx_consult_sessions_doctor ON consult_sessions(anonymized_doctor_id);

-- ------------------------------------------------------------------------------
-- 10. AUTOMATED UPDATED_AT TIMESTAMP TRIGGER
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name IN ('users', 'consents', 'salts', 'foods', 'rules', 'schedules', 'medicine_box', 'alarms', 'consult_sessions')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trg_update_timestamp_%I ON %I;
            CREATE TRIGGER trg_update_timestamp_%I
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_timestamp_column();
        ', tbl, tbl, tbl, tbl);
    END LOOP;
END;
$$;
