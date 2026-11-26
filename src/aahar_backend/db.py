"""SQLite persistence layer mirroring Supabase/PostgreSQL schema and DPDP controls."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator
import uuid

from .constants import DEFAULT_DB_PATH, VERIFIED_RULES_PATH
from .models import (
    ConsentCreateRequest,
    ConsentRecord,
    DataErasureResponse,
    PrivacyAuditSummary,
    ScanIngestRequest,
    ScanRecordResponse,
    TimetableResponse,
    UserCreateRequest,
    UserProfile,
)


class ConsentRequiredError(PermissionError):
    """Raised when an operation lacks active DB-recorded DPDP Act 2023 consent."""


class UserNotFoundError(KeyError):
    """Raised when referencing a non-existent or erased user_id."""


class AaharDatabase:
    """Relational repository supporting DPDP consent logs, verified rules, scans, and schedules."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        rules_path: Path | None = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.rules_path = rules_path or VERIFIED_RULES_PATH
        self._is_memory = str(self.db_path) == ":memory:"
        self._memory_conn: sqlite3.Connection | None = None
        if self._is_memory:
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self.seed_from_verified_rules(self.rules_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._is_memory:
            assert self._memory_conn is not None
            conn = self._memory_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return

        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    preferred_language TEXT NOT NULL DEFAULT 'en',
                    age_band TEXT NOT NULL DEFAULT 'adult',
                    created_at_utc TEXT NOT NULL,
                    erased_at_utc TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS consent_logs (
                    consent_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    consented INTEGER NOT NULL,
                    purpose TEXT NOT NULL,
                    retention_policy TEXT NOT NULL,
                    raw_images_stored INTEGER NOT NULL DEFAULT 0 CHECK (raw_images_stored = 0),
                    granted_at_utc TEXT NOT NULL,
                    withdrawn_at_utc TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS salts (
                    salt_id TEXT PRIMARY KEY,
                    salt_name TEXT NOT NULL UNIQUE,
                    drug_class TEXT NOT NULL,
                    rule_ids_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS foods (
                    food_id TEXT PRIMARY KEY,
                    food_name TEXT NOT NULL UNIQUE,
                    ifct_code TEXT NULL,
                    primary_nutrients_json TEXT NOT NULL,
                    clinical_note TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS rules (
                    rule_id TEXT PRIMARY KEY,
                    drug_class TEXT NOT NULL,
                    active_salts_json TEXT NOT NULL,
                    interfering_nutrients_json TEXT NOT NULL,
                    culprit_indian_foods_json TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    biochemical_mechanism TEXT NOT NULL,
                    ifct_evidence_json TEXT NOT NULL,
                    before_food_hours REAL NOT NULL,
                    after_food_hours REAL NOT NULL,
                    bioavailability_drop_pct REAL NOT NULL,
                    t_max_delay_hours REAL NOT NULL,
                    ghar_ki_rasoi_swaps_json TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    clinical_sign_off_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scan_records (
                    scan_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    consent_id TEXT NOT NULL REFERENCES consent_logs(consent_id),
                    active_salts_json TEXT NOT NULL,
                    confirmed_foods_json TEXT NOT NULL,
                    nutrient_flags_json TEXT NOT NULL,
                    meal_slot TEXT NOT NULL,
                    confirmed_by_user INTEGER NOT NULL CHECK (confirmed_by_user = 1),
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    consent_id TEXT NOT NULL REFERENCES consent_logs(consent_id),
                    medications_json TEXT NOT NULL,
                    meals_json TEXT NOT NULL,
                    conflict_count INTEGER NOT NULL,
                    timeline_json TEXT NOT NULL,
                    qr_health_pass_json TEXT NOT NULL,
                    safety_disclaimer TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                """
            )

    def seed_from_verified_rules(self, rules_path: Path) -> int:
        """Load Member 2's verified_rules.json into rules, salts, and foods tables."""
        raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
        salts_map: dict[str, dict] = {}
        foods_map: dict[str, dict] = {}

        with self._connect() as conn:
            for r in raw_rules:
                gap = r["safe_time_gap_hours"]
                impact = r["absorption_impact"]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rules (
                        rule_id, drug_class, active_salts_json, interfering_nutrients_json,
                        culprit_indian_foods_json, severity, interaction_type, biochemical_mechanism,
                        ifct_evidence_json, before_food_hours, after_food_hours,
                        bioavailability_drop_pct, t_max_delay_hours, ghar_ki_rasoi_swaps_json,
                        citations_json, clinical_sign_off_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["rule_id"],
                        r["drug_class"],
                        json.dumps(r["active_salts"]),
                        json.dumps(r["interfering_nutrients"]),
                        json.dumps(r["culprit_indian_foods"]),
                        r["severity"],
                        r.get("interaction_type", ""),
                        r.get("biochemical_mechanism") or r.get("interaction_type", ""),
                        json.dumps(r.get("ifct_evidence", [])),
                        float(gap["before_food_hours"]),
                        float(gap["after_food_hours"]),
                        float(impact["bioavailability_drop_pct"]),
                        float(impact["t_max_delay_hours"]),
                        json.dumps(r.get("ghar_ki_rasoi_swaps", [])),
                        json.dumps(r.get("citations", [])),
                        json.dumps(r.get("clinical_sign_off", {})),
                    ),
                )

                for salt in r["active_salts"]:
                    entry = salts_map.setdefault(
                        salt,
                        {
                            "salt_id": f"salt_{salt.lower().replace(' ', '_')}",
                            "salt_name": salt,
                            "drug_class": r["drug_class"],
                            "rule_ids": [],
                        },
                    )
                    if r["rule_id"] not in entry["rule_ids"]:
                        entry["rule_ids"].append(r["rule_id"])

                for ev in r.get("ifct_evidence", []):
                    fname = ev["food"]
                    f_entry = foods_map.setdefault(
                        fname,
                        {
                            "food_id": f"food_{fname.lower().replace(' ', '_').replace('/', '_')}",
                            "food_name": fname,
                            "ifct_code": ev.get("ifct_code"),
                            "nutrients": [],
                            "clinical_note": ev.get("clinical_note"),
                        },
                    )
                    if ev.get("primary_nutrient") and ev["primary_nutrient"] not in f_entry["nutrients"]:
                        f_entry["nutrients"].append(ev["primary_nutrient"])

                for food in r["culprit_indian_foods"]:
                    foods_map.setdefault(
                        food,
                        {
                            "food_id": f"food_{food.lower().replace(' ', '_').replace('/', '_')}",
                            "food_name": food,
                            "ifct_code": None,
                            "nutrients": list(r["interfering_nutrients"]),
                            "clinical_note": None,
                        },
                    )

            for s in salts_map.values():
                conn.execute(
                    "INSERT OR REPLACE INTO salts (salt_id, salt_name, drug_class, rule_ids_json) VALUES (?, ?, ?, ?)",
                    (s["salt_id"], s["salt_name"], s["drug_class"], json.dumps(s["rule_ids"])),
                )

            for fd in foods_map.values():
                conn.execute(
                    "INSERT OR REPLACE INTO foods (food_id, food_name, ifct_code, primary_nutrients_json, clinical_note) VALUES (?, ?, ?, ?, ?)",
                    (
                        fd["food_id"],
                        fd["food_name"],
                        fd["ifct_code"],
                        json.dumps(fd["nutrients"]),
                        fd["clinical_note"],
                    ),
                )
        return len(raw_rules)

    def create_user(self, req: UserCreateRequest) -> UserProfile:
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (user_id, preferred_language, age_band, created_at_utc) VALUES (?, ?, ?, ?)",
                (uid, req.preferred_language, req.age_band, now),
            )
        return UserProfile(
            user_id=uid,
            preferred_language=req.preferred_language,
            age_band=req.age_band,
            created_at_utc=now,
        )

    def record_consent(self, req: ConsentCreateRequest) -> ConsentRecord:
        now = datetime.now(timezone.utc).isoformat()
        cid = f"dpdp_{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            user_row = conn.execute(
                "SELECT user_id, erased_at_utc FROM users WHERE user_id = ?", (req.user_id,)
            ).fetchone()
            if user_row is None or user_row["erased_at_utc"] is not None:
                raise UserNotFoundError(f"Unknown or erased user_id: {req.user_id}")
            if not req.consented:
                # Log refusal if needed, then block downstream usage
                raise ConsentRequiredError(
                    "DPDP Act 2023 requires explicit affirmative user consent (consented=true)."
                )
            conn.execute(
                """
                INSERT INTO consent_logs (
                    consent_id, user_id, consented, purpose, retention_policy, raw_images_stored, granted_at_utc
                ) VALUES (?, ?, 1, ?, ?, 0, ?)
                """,
                (cid, req.user_id, req.purpose, req.retention_policy, now),
            )
        return ConsentRecord(
            consent_id=cid,
            user_id=req.user_id,
            consented=True,
            purpose=req.purpose,
            retention_policy=req.retention_policy,
            raw_images_stored=False,
            granted_at_utc=now,
        )

    def get_consent(self, consent_id: str) -> ConsentRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM consent_logs WHERE consent_id = ?", (consent_id,)
            ).fetchone()
        if row is None:
            raise ConsentRequiredError(f"Consent record '{consent_id}' not found.")
        return ConsentRecord(
            consent_id=row["consent_id"],
            user_id=row["user_id"],
            consented=bool(row["consented"]),
            purpose=row["purpose"],
            retention_policy=row["retention_policy"],
            raw_images_stored=False,
            granted_at_utc=row["granted_at_utc"],
            withdrawn_at_utc=row["withdrawn_at_utc"],
        )

    def require_active_consent(self, user_id: str, consent_id: str) -> ConsentRecord:
        """Enforce in DB that user has active, unwithdrawn DPDP consent before processing health data."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.*, u.erased_at_utc
                FROM consent_logs c
                JOIN users u ON u.user_id = c.user_id
                WHERE c.consent_id = ? AND c.user_id = ?
                """,
                (consent_id, user_id),
            ).fetchone()
        if row is None or row["erased_at_utc"] is not None:
            raise ConsentRequiredError(
                "No valid DPDP consent record found for this user_id and consent_id."
            )
        if not row["consented"] or row["withdrawn_at_utc"] is not None:
            raise ConsentRequiredError(
                "DPDP consent was withdrawn or refused; processing is blocked."
            )
        return ConsentRecord(
            consent_id=row["consent_id"],
            user_id=row["user_id"],
            consented=True,
            purpose=row["purpose"],
            retention_policy=row["retention_policy"],
            raw_images_stored=False,
            granted_at_utc=row["granted_at_utc"],
            withdrawn_at_utc=None,
        )

    def withdraw_consent(self, consent_id: str) -> ConsentRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE consent_logs SET withdrawn_at_utc = ? WHERE consent_id = ? AND withdrawn_at_utc IS NULL",
                (now, consent_id),
            )
            if cur.rowcount == 0:
                existing = conn.execute(
                    "SELECT consent_id FROM consent_logs WHERE consent_id = ?", (consent_id,)
                ).fetchone()
                if existing is None:
                    raise ConsentRequiredError(f"Consent '{consent_id}' not found.")
        return self.get_consent(consent_id)

    def erase_user_data(self, user_id: str) -> DataErasureResponse:
        """DPDP Act 2023 Right to Erasure: delete scans/schedules and mark consents withdrawn."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            user_row = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if user_row is None:
                raise UserNotFoundError(f"Unknown user_id: {user_id}")
            scans_del = conn.execute("DELETE FROM scan_records WHERE user_id = ?", (user_id,)).rowcount
            sched_del = conn.execute("DELETE FROM schedules WHERE user_id = ?", (user_id,)).rowcount
            cons_upd = conn.execute(
                "UPDATE consent_logs SET withdrawn_at_utc = COALESCE(withdrawn_at_utc, ?) WHERE user_id = ?",
                (now, user_id),
            ).rowcount
            conn.execute("UPDATE users SET erased_at_utc = ? WHERE user_id = ?", (now, user_id))
        return DataErasureResponse(
            user_id=user_id,
            erased=True,
            scans_deleted=scans_del,
            schedules_deleted=sched_del,
            consents_withdrawn=cons_upd,
            message="User health scans and schedules erased; consents marked withdrawn per DPDP Act 2023.",
        )

    def save_scan_metadata(self, req: ScanIngestRequest) -> ScanRecordResponse:
        self.require_active_consent(req.user_id, req.consent_id)
        sid = f"scan_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scan_records (
                    scan_id, user_id, consent_id, active_salts_json, confirmed_foods_json,
                    nutrient_flags_json, meal_slot, confirmed_by_user, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    sid,
                    req.user_id,
                    req.consent_id,
                    json.dumps(req.active_salts),
                    json.dumps(req.confirmed_foods),
                    json.dumps(req.nutrient_flags),
                    req.meal_slot,
                    now,
                ),
            )
        return ScanRecordResponse(
            scan_id=sid,
            user_id=req.user_id,
            consent_id=req.consent_id,
            active_salts=req.active_salts,
            confirmed_foods=req.confirmed_foods,
            nutrient_flags=req.nutrient_flags,
            meal_slot=req.meal_slot,
            raw_images_stored=False,
            created_at_utc=now,
        )

    def save_schedule(
        self,
        response: TimetableResponse,
        medications: list[dict],
        meals: list[dict],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO schedules (
                    schedule_id, user_id, consent_id, medications_json, meals_json,
                    conflict_count, timeline_json, qr_health_pass_json, safety_disclaimer, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.schedule_id,
                    response.user_id,
                    response.consent_id,
                    json.dumps(medications),
                    json.dumps(meals),
                    response.conflict_count,
                    json.dumps([t.model_dump(mode="json") for t in response.timeline]),
                    json.dumps(response.qr_health_pass.model_dump(mode="json")),
                    response.safety_disclaimer,
                    response.created_at_utc,
                ),
            )

    def get_schedule(self, schedule_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Schedule '{schedule_id}' not found.")
        return {
            "schedule_id": row["schedule_id"],
            "user_id": row["user_id"],
            "consent_id": row["consent_id"],
            "medications": json.loads(row["medications_json"]),
            "meals": json.loads(row["meals_json"]),
            "conflict_count": row["conflict_count"],
            "timeline": json.loads(row["timeline_json"]),
            "qr_health_pass": json.loads(row["qr_health_pass_json"]),
            "safety_disclaimer": row["safety_disclaimer"],
            "created_at_utc": row["created_at_utc"],
        }

    def list_rules(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM rules ORDER BY rule_id").fetchall()
        return [
            {
                "rule_id": r["rule_id"],
                "drug_class": r["drug_class"],
                "active_salts": json.loads(r["active_salts_json"]),
                "interfering_nutrients": json.loads(r["interfering_nutrients_json"]),
                "culprit_indian_foods": json.loads(r["culprit_indian_foods_json"]),
                "severity": r["severity"],
                "interaction_type": r["interaction_type"],
                "biochemical_mechanism": r["biochemical_mechanism"],
                "ifct_evidence": json.loads(r["ifct_evidence_json"]),
                "safe_time_gap_hours": {
                    "before_food_hours": r["before_food_hours"],
                    "after_food_hours": r["after_food_hours"],
                },
                "absorption_impact": {
                    "bioavailability_drop_pct": r["bioavailability_drop_pct"],
                    "t_max_delay_hours": r["t_max_delay_hours"],
                },
                "ghar_ki_rasoi_swaps": json.loads(r["ghar_ki_rasoi_swaps_json"]),
                "citations": json.loads(r["citations_json"]),
                "clinical_sign_off": json.loads(r["clinical_sign_off_json"]),
            }
            for r in rows
        ]

    def list_salts(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM salts ORDER BY salt_name").fetchall()
        return [
            {
                "salt_id": r["salt_id"],
                "salt_name": r["salt_name"],
                "drug_class": r["drug_class"],
                "rule_ids": json.loads(r["rule_ids_json"]),
            }
            for r in rows
        ]

    def list_foods(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM foods ORDER BY food_name").fetchall()
        return [
            {
                "food_id": r["food_id"],
                "food_name": r["food_name"],
                "ifct_code": r["ifct_code"],
                "primary_nutrients": json.loads(r["primary_nutrients_json"]),
                "clinical_note": r["clinical_note"],
            }
            for r in rows
        ]

    def get_privacy_audit_summary(self) -> PrivacyAuditSummary:
        with self._connect() as conn:
            active_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE erased_at_utc IS NULL"
            ).fetchone()[0]
            active_consents = conn.execute(
                "SELECT COUNT(*) FROM consent_logs WHERE consented = 1 AND withdrawn_at_utc IS NULL"
            ).fetchone()[0]
            withdrawn_consents = conn.execute(
                "SELECT COUNT(*) FROM consent_logs WHERE withdrawn_at_utc IS NOT NULL"
            ).fetchone()[0]
            scans_count = conn.execute("SELECT COUNT(*) FROM scan_records").fetchone()[0]
            sched_count = conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
            rules_count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]

        return PrivacyAuditSummary(
            dpdp_compliant=True,
            raw_images_stored_count=0,
            active_users_count=active_users,
            active_consents_count=active_consents,
            withdrawn_consents_count=withdrawn_consents,
            stored_scans_count=scans_count,
            stored_schedules_count=sched_count,
            verified_rules_loaded=rules_count,
        )
