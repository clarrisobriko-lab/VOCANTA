import json
import sqlite3
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_DIR, DATABASE_FILE
from automation.idempotency import canonicalize_job_url
from core.models import Job


VALID_STATUSES = {
    "NEW",
    "SHORTLISTED",
    "PREPARING",
    "APPLIED",
    "FOLLOW_UP",
    "INTERVIEW",
    "REJECTED",
    "OFFER",
}

APPLICATION_RUN_STATUSES = {
    "CREATED",
    "PREPARING",
    "FORM_FILLED",
    "READY_TO_REVIEW",
    "HUMAN_VERIFICATION",
    "MANUAL_REQUIRED",
    "SUBMITTING",
    "SUBMITTED",
    "CONFIRMED",
    "UNKNOWN",
    "FAILED",
    "BLOCKED",
}

APPLICATION_RUN_TRANSITIONS = {
    "CREATED": {"PREPARING", "BLOCKED", "FAILED"},
    "PREPARING": {
        "FORM_FILLED",
        "READY_TO_REVIEW",
        "HUMAN_VERIFICATION",
        "MANUAL_REQUIRED",
        "FAILED",
    },
    "FORM_FILLED": {
        "FORM_FILLED",
        "READY_TO_REVIEW",
        "HUMAN_VERIFICATION",
        "MANUAL_REQUIRED",
        "SUBMITTING",
        "FAILED",
    },
    "SUBMITTING": {"SUBMITTED", "UNKNOWN", "FAILED"},
    "SUBMITTED": {"CONFIRMED", "UNKNOWN"},
    "READY_TO_REVIEW": {"CONFIRMED", "UNKNOWN"},
    "HUMAN_VERIFICATION": {"CONFIRMED", "UNKNOWN"},
    "MANUAL_REQUIRED": {"CONFIRMED", "UNKNOWN"},
    "UNKNOWN": {"CONFIRMED"},
    "FAILED": set(),
    "BLOCKED": set(),
    "CONFIRMED": set(),
}

NOTIFICATION_DELIVERY_STATUSES = {
    "QUEUED",
    "SENDING",
    "SENT",
    "AUTH_REQUIRED",
    "OUTBOX",
    "FAILED",
}


class Database:
    def __init__(self, database_file: Path | str = DATABASE_FILE) -> None:
        self.database_file = Path(database_file)
        self.database_file.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.database_file)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA busy_timeout = 5000")

        self._create_schema()
        self._migrate_schema()
        self._backfill_application_history()

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                canonical_url TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                salary TEXT NOT NULL DEFAULT '',
                employment_type TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'NEW',
                applied INTEGER NOT NULL DEFAULT 0,
                applied_date TEXT,
                follow_up_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS application_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                changed_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                screenshot_path TEXT NOT NULL DEFAULT '',
                attempted_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_intelligence (
                job_url TEXT PRIMARY KEY,
                sponsorship_score INTEGER NOT NULL DEFAULT 0,
                sponsorship_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                relocation_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                international_hiring_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                confidence INTEGER NOT NULL DEFAULT 0,
                ngo_label TEXT NOT NULL DEFAULT 'CORPORATE',
                blocked INTEGER NOT NULL DEFAULT 0,
                block_reason TEXT NOT NULL DEFAULT '',
                block_category TEXT NOT NULL DEFAULT '',
                recommendation TEXT NOT NULL DEFAULT 'APPLY',
                decision_verdict TEXT NOT NULL DEFAULT 'REVIEW',
                decision_reason_codes TEXT NOT NULL DEFAULT '',
                decision_evidence TEXT NOT NULL DEFAULT '',
                rule_version TEXT NOT NULL DEFAULT '',
                primary_reason TEXT NOT NULL DEFAULT '',
                assessed_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS application_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                candidate_profile_hash TEXT NOT NULL,
                document_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                confirmation_text TEXT NOT NULL DEFAULT '',
                confirmation_url TEXT NOT NULL DEFAULT '',
                active_url TEXT NOT NULL DEFAULT '',
                screenshot_path TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                dedup_key TEXT NOT NULL UNIQUE,
                channel TEXT NOT NULL DEFAULT 'EMAIL',
                auth_mode TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'QUEUED',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error_code TEXT NOT NULL DEFAULT '',
                outbox_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sent_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employer_memory (
                company TEXT PRIMARY KEY,
                applications INTEGER NOT NULL DEFAULT 0,
                interviews INTEGER NOT NULL DEFAULT 0,
                rejections INTEGER NOT NULL DEFAULT 0,
                offers INTEGER NOT NULL DEFAULT 0,
                automation_attempts INTEGER NOT NULL DEFAULT 0,
                automation_successes INTEGER NOT NULL DEFAULT 0,
                automation_success_rate REAL NOT NULL DEFAULT 0,
                sponsorship_score INTEGER NOT NULL DEFAULT 0,
                last_contact TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS human_action_queue (
                job_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                job_score INTEGER NOT NULL DEFAULT 0,
                opportunity_score INTEGER NOT NULL DEFAULT 0,
                email_status TEXT NOT NULL DEFAULT '',
                email_location TEXT NOT NULL DEFAULT '',
                queued_at TEXT NOT NULL,
                resolved_at TEXT,
                resolution_notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_queue_audit (
                queue_id TEXT PRIMARY KEY,
                job_id INTEGER NOT NULL,
                stage TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_status_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                reason TEXT NOT NULL,
                stage TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_job ON application_history(job_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_automation_job ON automation_attempts(job_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_application_runs_job ON application_runs(job_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_notification_job ON notification_deliveries(job_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_queue_audit_job ON automation_queue_audit(job_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_status_audit_job ON job_status_audit(job_id)"
        )
        self.connection.commit()

    def _migrate_schema(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(jobs)").fetchall()
        }
        migrations = {
            "status": "ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'NEW'",
            "applied": "ALTER TABLE jobs ADD COLUMN applied INTEGER NOT NULL DEFAULT 0",
            "applied_date": "ALTER TABLE jobs ADD COLUMN applied_date TEXT",
            "follow_up_date": "ALTER TABLE jobs ADD COLUMN follow_up_date TEXT",
            "notes": "ALTER TABLE jobs ADD COLUMN notes TEXT NOT NULL DEFAULT ''",
            "updated_at": "ALTER TABLE jobs ADD COLUMN updated_at TEXT",
            "canonical_url": (
                "ALTER TABLE jobs ADD COLUMN canonical_url TEXT NOT NULL DEFAULT ''"
            ),
        }
        for column, sql in migrations.items():
            if column not in columns:
                self.connection.execute(sql)

        intelligence_columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(job_intelligence)"
            ).fetchall()
        }
        intelligence_migrations = {
            "decision_verdict": (
                "ALTER TABLE job_intelligence ADD COLUMN "
                "decision_verdict TEXT NOT NULL DEFAULT 'REVIEW'"
            ),
            "decision_reason_codes": (
                "ALTER TABLE job_intelligence ADD COLUMN "
                "decision_reason_codes TEXT NOT NULL DEFAULT ''"
            ),
            "decision_evidence": (
                "ALTER TABLE job_intelligence ADD COLUMN "
                "decision_evidence TEXT NOT NULL DEFAULT ''"
            ),
            "rule_version": (
                "ALTER TABLE job_intelligence ADD COLUMN "
                "rule_version TEXT NOT NULL DEFAULT ''"
            ),
            "primary_reason": (
                "ALTER TABLE job_intelligence ADD COLUMN "
                "primary_reason TEXT NOT NULL DEFAULT ''"
            ),
        }
        for column, sql in intelligence_migrations.items():
            if column not in intelligence_columns:
                self.connection.execute(sql)

        run_columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(application_runs)"
            ).fetchall()
        }
        if "active_url" not in run_columns:
            self.connection.execute(
                "ALTER TABLE application_runs ADD COLUMN "
                "active_url TEXT NOT NULL DEFAULT ''"
            )

        rows = self.connection.execute(
            "SELECT id, url FROM jobs WHERE canonical_url = ''"
        ).fetchall()
        for row in rows:
            self.connection.execute(
                "UPDATE jobs SET canonical_url = ? WHERE id = ?",
                (canonicalize_job_url(row["url"]), row["id"]),
            )

        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_canonical_url ON jobs(canonical_url)"
        )

        self.connection.execute(
            """
            INSERT INTO schema_metadata(key, value)
            VALUES('schema_version', '2.6.1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )
        self.connection.commit()

    def _backfill_application_history(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        candidates = self.connection.execute(
            """
            SELECT
                j.id,
                j.status,
                j.notes,
                COALESCE(
                    NULLIF(j.applied_date, ''),
                    NULLIF(j.updated_at, ''),
                    NULLIF(j.last_seen_at, ''),
                    NULLIF(j.first_seen_at, ''),
                    ?
                ) AS changed_at
            FROM jobs AS j
            WHERE j.status != 'NEW'
              AND NOT EXISTS (
                  SELECT 1
                  FROM application_history AS h
                  WHERE h.job_id = j.id
              )
            """,
            (now,),
        ).fetchall()

        if not candidates:
            return 0

        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO application_history(
                    job_id,
                    old_status,
                    new_status,
                    notes,
                    changed_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id"],
                        "IMPORTED",
                        row["status"],
                        row["notes"] or "",
                        row["changed_at"],
                    )
                    for row in candidates
                ],
            )
        return len(candidates)

    def repair_history(self) -> int:
        return self._backfill_application_history()

    def has_confirmed_submission(self, job_id: int) -> bool:
        """Return True only when VOCANTA has durable evidence of a submission."""
        row = self.connection.execute(
            """
            SELECT CASE WHEN
                EXISTS (
                    SELECT 1 FROM application_runs r
                    WHERE r.job_id = ? AND r.status IN ('SUBMITTED', 'CONFIRMED')
                )
                OR EXISTS (
                    SELECT 1 FROM automation_attempts a
                    WHERE a.job_id = ? AND a.status IN ('AUTO_SUBMITTED', 'SUBMITTED')
                )
            THEN 1 ELSE 0 END AS confirmed
            """,
            (job_id, job_id),
        ).fetchone()
        return bool(row and row["confirmed"])

    def repair_job_statuses(self, stage: str = "STARTUP") -> list[sqlite3.Row]:
        """Repair every FOLLOW_UP state that has no durable submission evidence.

        Application history alone is not submission evidence. FOLLOW_UP is valid only after a confirmed submission. Browser preparation,
        form filling, human verification, manual review, notifications, or failed
        automation runs are not applications and must not block a fresh retry.
        """
        candidates = list(
            self.connection.execute(
                """
                SELECT j.id, j.company, j.title, j.status
                FROM jobs AS j
                WHERE j.status = 'FOLLOW_UP'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM application_runs AS r
                      WHERE r.job_id = j.id
                        AND r.status IN ('SUBMITTED', 'CONFIRMED')
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM automation_attempts AS a
                      WHERE a.job_id = j.id
                        AND a.status IN ('AUTO_SUBMITTED', 'SUBMITTED')
                  )
                ORDER BY j.id
                """
            ).fetchall()
        )
        if not candidates:
            return []

        changed_at = datetime.now(timezone.utc).isoformat()
        reason = (
            "FOLLOW_UP had no confirmed submission evidence; reset to NEW so the "
            "eligible job can enter automation"
        )
        normalized_stage = stage.strip().upper() or "STARTUP"
        with self.connection:
            for row in candidates:
                self.connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'NEW', applied = 0, applied_date = NULL,
                        follow_up_date = NULL, notes = '', updated_at = ?
                    WHERE id = ?
                    """,
                    (changed_at, row["id"]),
                )
                self.connection.execute(
                    """
                    INSERT INTO job_status_audit(
                        job_id, previous_status, new_status, reason, stage, changed_at
                    ) VALUES(?, 'FOLLOW_UP', 'NEW', ?, ?, ?)
                    """,
                    (row["id"], reason, normalized_stage, changed_at),
                )
                self.connection.execute(
                    """
                    INSERT INTO application_history(
                        job_id, old_status, new_status, notes, changed_at
                    ) VALUES(?, 'FOLLOW_UP', 'NEW', ?, ?)
                    """,
                    (row["id"], reason, changed_at),
                )
        return candidates


    def upsert_job(self, job: Job) -> None:
        now = datetime.now(timezone.utc).isoformat()
        canonical_url = canonicalize_job_url(job.url)
        existing = self.connection.execute(
            "SELECT id FROM jobs WHERE canonical_url = ? LIMIT 1",
            (canonical_url,),
        ).fetchone()
        if existing is not None:
            self.connection.execute(
                """
                UPDATE jobs
                SET company = ?, title = ?, location = ?, source = ?,
                    description = ?, salary = ?, employment_type = ?,
                    score = ?, last_seen_at = ?, canonical_url = ?
                WHERE id = ?
                """,
                (
                    job.company,
                    job.title,
                    job.location,
                    job.source,
                    job.description,
                    job.salary,
                    job.employment_type,
                    job.score,
                    now,
                    canonical_url,
                    existing["id"],
                ),
            )
            return
        self.connection.execute(
            """
            INSERT INTO jobs (
                company, title, location, source, url, canonical_url, description,
                salary, employment_type, score, first_seen_at, last_seen_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                company = excluded.company,
                title = excluded.title,
                location = excluded.location,
                source = excluded.source,
                description = excluded.description,
                salary = excluded.salary,
                employment_type = excluded.employment_type,
                score = excluded.score,
                last_seen_at = excluded.last_seen_at,
                canonical_url = excluded.canonical_url
            """,
            (
                job.company,
                job.title,
                job.location,
                job.source,
                job.url,
                canonical_url,
                job.description,
                job.salary,
                job.employment_type,
                job.score,
                now,
                now,
                now,
            ),
        )

    def upsert_jobs(self, jobs: Iterable[Job]) -> int:
        count = 0
        with self.connection:
            for job in jobs:
                self.upsert_job(job)
                count += 1
        return count

    def list_jobs(
        self,
        minimum_score: int = 0,
        limit: int | None = None,
    ) -> list[sqlite3.Row]:
        sql = """
            SELECT j.id, j.company, j.title, j.location, j.source, j.url,
                   j.score, j.status, j.applied, j.applied_date,
                   j.follow_up_date, j.notes, j.updated_at,
                   COALESCE(i.sponsorship_label, 'UNKNOWN') AS sponsorship_label,
                   COALESCE(i.relocation_label, 'UNKNOWN') AS relocation_label,
                   COALESCE(i.ngo_label, 'CORPORATE') AS ngo_label,
                   CASE
                       WHEN COALESCE(i.recommendation, 'APPLY') IN ('PRIORITY', 'APPLY')
                            AND (j.status NOT IN ('NEW', 'SHORTLISTED', 'PREPARING')
                                 OR COALESCE(i.blocked, 0) = 1
                                 OR COALESCE(i.decision_verdict, 'REVIEW') NOT IN ('PRIORITY', 'APPLY')
                                 OR EXISTS (SELECT 1 FROM application_runs r WHERE r.job_id = j.id)
                                 OR EXISTS (
                                     SELECT 1 FROM automation_attempts a
                                     WHERE a.job_id = j.id
                                       AND a.status IN ('AUTO_SUBMITTED', 'READY_TO_REVIEW',
                                                        'HUMAN_VERIFICATION', 'SUBMITTED',
                                                        'MANUAL_REQUIRED')
                                 ))
                       THEN 'NOT_QUEUED'
                       ELSE COALESCE(i.recommendation, 'REVIEW')
                   END AS recommendation,
                   COALESCE(i.confidence, 0) AS intelligence_confidence,
                   COALESCE(i.decision_verdict, 'REVIEW') AS decision_verdict,
                   COALESCE(i.decision_reason_codes, '') AS decision_reason_codes,
                   COALESCE(i.rule_version, '') AS rule_version
            FROM jobs AS j
            LEFT JOIN job_intelligence AS i ON i.job_url = j.url
            WHERE j.score >= ?
            ORDER BY
                CASE COALESCE(i.recommendation, 'APPLY')
                    WHEN 'PRIORITY' THEN 1
                    WHEN 'APPLY' THEN 2
                    WHEN 'RESEARCH' THEN 3
                    ELSE 4
                END,
                j.score DESC,
                j.company ASC,
                j.title ASC
        """
        params: list[object] = [minimum_score]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return list(self.connection.execute(sql, params).fetchall())

    def list_applications(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT id, company, title, location, source, url, score, status,
                       applied, applied_date, follow_up_date, notes, updated_at
                FROM jobs
                WHERE status != 'NEW'
                ORDER BY
                    CASE status
                        WHEN 'OFFER' THEN 1
                        WHEN 'INTERVIEW' THEN 2
                        WHEN 'FOLLOW_UP' THEN 3
                        WHEN 'APPLIED' THEN 4
                        WHEN 'PREPARING' THEN 5
                        WHEN 'SHORTLISTED' THEN 6
                        WHEN 'REJECTED' THEN 7
                        ELSE 8
                    END,
                    score DESC
                """
            ).fetchall()
        )

    def list_due_follow_ups(self) -> list[sqlite3.Row]:
        today = datetime.now(timezone.utc).date().isoformat()
        return list(
            self.connection.execute(
                """
                SELECT id, company, title, location, url, score, status,
                       applied_date, follow_up_date, notes
                FROM jobs
                WHERE follow_up_date IS NOT NULL
                  AND follow_up_date != ''
                  AND follow_up_date <= ?
                  AND status IN ('APPLIED', 'FOLLOW_UP')
                ORDER BY follow_up_date ASC, score DESC
                """,
                (today,),
            ).fetchall()
        )

    def update_application(
        self,
        job_id: int,
        status: str,
        notes: str = "",
        follow_up_date: str | None = None,
    ) -> None:
        normalized = status.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError(f"Unsupported status: {status}")

        current = self.get_job(job_id)
        if current is None:
            raise ValueError("Job not found")

        if normalized == "FOLLOW_UP":
            allowed_from_applied = current["status"] == "APPLIED"
            if not allowed_from_applied and not self.has_confirmed_submission(job_id):
                raise ValueError(
                    "FOLLOW_UP requires a confirmed submission or an existing APPLIED status"
                )

        now = datetime.now(timezone.utc).isoformat()
        applied = int(
            normalized
            in {"APPLIED", "FOLLOW_UP", "INTERVIEW", "REJECTED", "OFFER"}
        )
        applied_date = now if applied else None
        clean_notes = notes.strip()

        with self.connection:
            self.connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    applied = ?,
                    applied_date = COALESCE(applied_date, ?),
                    follow_up_date = ?,
                    notes = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    normalized,
                    applied,
                    applied_date,
                    follow_up_date or None,
                    clean_notes,
                    now,
                    job_id,
                ),
            )
            self.connection.execute(
                """
                INSERT INTO application_history(
                    job_id,
                    old_status,
                    new_status,
                    notes,
                    changed_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    current["status"],
                    normalized,
                    clean_notes,
                    now,
                ),
            )

    def mark_applied_with_follow_up(
        self,
        job_id: int,
        notes: str,
        follow_up_date: str,
    ) -> None:
        self.update_application(
            job_id=job_id,
            status="APPLIED",
            notes=notes,
            follow_up_date=follow_up_date,
        )

    def get_job(self, job_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, company, title, location, source, url, description,
                   salary, employment_type, score, status, applied,
                   applied_date, follow_up_date, notes, updated_at
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()

    def get_history(self, job_id: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT old_status, new_status, notes, changed_at
                FROM application_history
                WHERE job_id = ?
                ORDER BY changed_at DESC, id DESC
                """,
                (job_id,),
            ).fetchall()
        )

    def analytics(self, shortlist_score: int) -> dict[str, int | float]:
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) AS shortlisted,
                SUM(CASE WHEN status = 'APPLIED' THEN 1 ELSE 0 END) AS applied,
                SUM(CASE WHEN status = 'FOLLOW_UP' THEN 1 ELSE 0 END) AS follow_ups,
                SUM(CASE WHEN status = 'INTERVIEW' THEN 1 ELSE 0 END) AS interviews,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN status = 'OFFER' THEN 1 ELSE 0 END) AS offers
            FROM jobs
            """,
            (shortlist_score,),
        ).fetchone()

        applied_total = sum(
            int(row[name] or 0)
            for name in ("applied", "follow_ups", "interviews", "rejected", "offers")
        )
        interviews = int(row["interviews"] or 0)
        offers = int(row["offers"] or 0)

        return {
            "total": int(row["total"] or 0),
            "shortlisted": int(row["shortlisted"] or 0),
            "applied": applied_total,
            "follow_ups": int(row["follow_ups"] or 0),
            "interviews": interviews,
            "rejected": int(row["rejected"] or 0),
            "offers": offers,
            "interview_rate": round(interviews / applied_total * 100, 1)
            if applied_total
            else 0.0,
            "offer_rate": round(offers / applied_total * 100, 1)
            if applied_total
            else 0.0,
        }

    def statistics(self, shortlist_score: int) -> dict[str, int]:
        data = self.analytics(shortlist_score)
        return {
            "total": int(data["total"]),
            "relevant": int(data["total"]),
            "shortlisted": int(data["shortlisted"]),
            "applied": int(data["applied"]),
            "follow_ups": int(data["follow_ups"]),
            "interviews": int(data["interviews"]),
            "offers": int(data["offers"]),
        }


    def status_counts(self, minimum_score: int = 0) -> dict[str, int]:
        rows = self.connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM jobs
            WHERE score >= ?
            GROUP BY status
            """,
            (minimum_score,),
        ).fetchall()

        counts = {status: 0 for status in VALID_STATUSES}
        for row in rows:
            counts[row["status"]] = int(row["count"] or 0)
        return counts

    def search_jobs(
        self,
        query: str,
        minimum_score: int = 0,
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        term = f"%{query.strip().lower()}%"
        return list(
            self.connection.execute(
                """
                SELECT id, company, title, location, source, url, score, status,
                       applied, applied_date, follow_up_date, notes, updated_at
                FROM jobs
                WHERE score >= ?
                  AND (
                      LOWER(company) LIKE ?
                      OR LOWER(title) LIKE ?
                      OR LOWER(location) LIKE ?
                      OR LOWER(source) LIKE ?
                      OR LOWER(notes) LIKE ?
                  )
                ORDER BY score DESC, company ASC, title ASC
                LIMIT ?
                """,
                (
                    minimum_score,
                    term,
                    term,
                    term,
                    term,
                    term,
                    limit,
                ),
            ).fetchall()
        )

    def operational_statistics(self, minimum_score: int = 0) -> dict[str, object]:
        status_counts = self.status_counts(minimum_score)
        average_score_row = self.connection.execute(
            """
            SELECT AVG(score) AS average_score
            FROM jobs
            WHERE score >= ?
            """,
            (minimum_score,),
        ).fetchone()

        week_start = datetime.now(timezone.utc).date().isoformat()
        applications_week = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM jobs
            WHERE applied_date IS NOT NULL
              AND DATE(applied_date) >= DATE(?, '-6 days')
            """,
            (week_start,),
        ).fetchone()

        interviews_month = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM application_history
            WHERE new_status = 'INTERVIEW'
              AND strftime('%Y-%m', changed_at) = strftime('%Y-%m', 'now')
            """
        ).fetchone()

        top_companies = list(
            self.connection.execute(
                """
                SELECT company, COUNT(*) AS count
                FROM jobs
                WHERE applied = 1
                GROUP BY company
                ORDER BY count DESC, company ASC
                LIMIT 5
                """
            ).fetchall()
        )

        return {
            "status_counts": status_counts,
            "average_score": round(
                float(average_score_row["average_score"] or 0.0),
                1,
            ),
            "applications_this_week": int(applications_week["count"] or 0),
            "interviews_this_month": int(interviews_month["count"] or 0),
            "top_companies": top_companies,
        }


    def list_application_candidates(
        self,
        minimum_score: int,
        limit: int = 30,
    ) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT id, company, title, location, source, url, description,
                       employment_type, score, status, applied, applied_date,
                       follow_up_date, notes, updated_at
                FROM jobs
                WHERE score >= ?
                  AND status IN ('NEW', 'SHORTLISTED', 'PREPARING')
                ORDER BY
                    CASE status
                        WHEN 'PREPARING' THEN 1
                        WHEN 'SHORTLISTED' THEN 2
                        ELSE 3
                    END,
                    score DESC,
                    company ASC,
                    title ASC
                LIMIT ?
                """,
                (minimum_score, limit),
            ).fetchall()
        )


    def terminal_automation_reason_for_url(self, url: str) -> str | None:
        """Return a terminal disposition for a previously processed job URL.

        This check is intentionally URL based so repeated connector discoveries are
        suppressed before persistence, queue auditing, dashboard display, and browser
        automation. Temporary failures are not terminal and remain retryable.
        """
        canonical_url = canonicalize_job_url(url)
        row = self.connection.execute(
            """
            SELECT a.status, a.message
            FROM jobs AS j
            JOIN automation_attempts AS a ON a.job_id = j.id
            WHERE (j.url = ? OR j.canonical_url = ?)
              AND a.status IN (
                    'AUTO_SUBMITTED', 'READY_TO_REVIEW', 'HUMAN_VERIFICATION',
                    'SUBMITTED', 'MANUAL_REQUIRED', 'SKIPPED_SOURCE'
              )
            ORDER BY a.attempted_at DESC, a.id DESC
            LIMIT 1
            """,
            (url, canonical_url),
        ).fetchone()
        if row is None:
            run = self.connection.execute(
                """
                SELECT r.status, r.last_error
                FROM jobs AS j
                JOIN application_runs AS r ON r.job_id = j.id
                WHERE (j.url = ? OR j.canonical_url = ?)
                  AND r.status IN (
                        'READY_TO_REVIEW', 'HUMAN_VERIFICATION', 'MANUAL_REQUIRED',
                        'SUBMITTED', 'CONFIRMED', 'BLOCKED'
                  )
                ORDER BY r.updated_at DESC, r.id DESC
                LIMIT 1
                """,
                (url, canonical_url),
            ).fetchone()
            if run is None:
                return None
            detail = (run['last_error'] or '').strip()
            return f"Terminal application run already exists: {run['status']}" + (f" ({detail})" if detail else '')
        detail = (row['message'] or '').strip()
        return f"Terminal automation attempt already exists: {row['status']}" + (f" ({detail})" if detail else '')

    def _automation_queue_reason_sql(self) -> str:
        return """
            CASE
                WHEN j.status NOT IN ('NEW', 'SHORTLISTED', 'PREPARING') THEN
                    'Status is not queueable: ' || j.status
                WHEN j.score < ? THEN 'Score below automation threshold'
                WHEN i.job_url IS NULL THEN 'Job intelligence is missing'
                WHEN COALESCE(i.blocked, 0) = 1 THEN
                    COALESCE(NULLIF(i.block_reason, ''), 'Blocked by intelligence rules')
                WHEN i.decision_verdict NOT IN ('PRIORITY', 'APPLY') THEN
                    COALESCE(NULLIF(i.primary_reason, ''), 'Eligibility not confirmed')
                WHEN EXISTS (
                    SELECT 1 FROM automation_attempts a
                    WHERE a.job_id = j.id
                      AND a.status IN ('AUTO_SUBMITTED', 'READY_TO_REVIEW',
                                       'HUMAN_VERIFICATION', 'SUBMITTED',
                                       'MANUAL_REQUIRED')
                ) THEN 'A terminal automation attempt already exists'
                WHEN EXISTS (
                    SELECT 1 FROM application_runs r
                    WHERE r.job_id = j.id
                ) THEN 'Application run already exists'
                ELSE 'ACCEPTED'
            END
        """

    def audit_automation_queue(self, minimum_score: int) -> list[sqlite3.Row]:
        reason_sql = self._automation_queue_reason_sql()
        rows = list(
            self.connection.execute(
                f"""
                SELECT j.id, j.company, j.title, j.url, j.score, j.status,
                       COALESCE(i.decision_verdict, 'REVIEW') AS decision_verdict,
                       {reason_sql} AS queue_reason
                FROM jobs AS j
                LEFT JOIN job_intelligence AS i ON i.job_url = j.url
                WHERE j.score >= ? OR i.recommendation IN ('PRIORITY', 'APPLY')
                ORDER BY j.score DESC, j.company ASC, j.title ASC
                """,
                (minimum_score, minimum_score),
            ).fetchall()
        )
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            for row in rows:
                queue_id = str(uuid.uuid4())
                decision = 'ACCEPTED' if row['queue_reason'] == 'ACCEPTED' else 'REJECTED'
                self.connection.execute(
                    """
                    INSERT INTO automation_queue_audit(
                        queue_id, job_id, stage, decision, reason, created_at
                    ) VALUES(?, ?, 'QUEUE_BUILD', ?, ?, ?)
                    """,
                    (queue_id, row['id'], decision, row['queue_reason'], now),
                )
        return rows

    def record_queue_audit(
        self, job_id: int, stage: str, decision: str, reason: str
    ) -> str:
        queue_id = str(uuid.uuid4())
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO automation_queue_audit(
                    queue_id, job_id, stage, decision, reason, created_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    job_id,
                    stage.strip().upper(),
                    decision.strip().upper(),
                    reason.strip(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return queue_id

    def automation_queue_decision_for_job(
        self, job_id: int, minimum_score: int
    ) -> sqlite3.Row | None:
        self.repair_job_statuses("PRE_QUEUE_DECISION")
        reason_sql = self._automation_queue_reason_sql()
        return self.connection.execute(
            f"""
            SELECT j.id, j.company, j.title, j.score,
                   {reason_sql} AS reason
            FROM jobs AS j
            LEFT JOIN job_intelligence AS i ON i.job_url = j.url
            WHERE j.id = ?
            """,
            (minimum_score, job_id),
        ).fetchone()

    def automation_queue_count(self, minimum_score: int) -> int:
        self.repair_job_statuses("PRE_QUEUE_COUNT")
        reason_sql = self._automation_queue_reason_sql()
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM jobs AS j
            JOIN job_intelligence AS i ON i.job_url = j.url
            WHERE ({reason_sql}) = 'ACCEPTED'
            """,
            (minimum_score,),
        ).fetchone()
        return int(row['count'] or 0)

    def automation_queue_diagnostics(
        self, minimum_score: int, limit: int = 20
    ) -> list[sqlite3.Row]:
        self.repair_job_statuses("PRE_QUEUE_DIAGNOSTICS")
        reason_sql = self._automation_queue_reason_sql()
        return list(
            self.connection.execute(
                f"""
                SELECT j.id, j.company, j.title, j.score, j.status,
                       COALESCE(i.decision_verdict, 'REVIEW') AS decision_verdict,
                       {reason_sql} AS reason
                FROM jobs AS j
                LEFT JOIN job_intelligence AS i ON i.job_url = j.url
                WHERE j.score >= ? OR i.recommendation IN ('PRIORITY', 'APPLY')
                ORDER BY
                    CASE WHEN ({reason_sql}) = 'ACCEPTED' THEN 0 ELSE 1 END,
                    j.score DESC, j.company ASC, j.title ASC
                LIMIT ?
                """,
                (minimum_score, minimum_score, minimum_score, limit),
            ).fetchall()
        )

    def list_automation_candidates(
        self,
        minimum_score: int,
        limit: int,
    ) -> list[sqlite3.Row]:
        self.repair_job_statuses("PRE_QUEUE_BUILD")
        reason_sql = self._automation_queue_reason_sql()
        rows = list(
            self.connection.execute(
                f"""
                SELECT lower(hex(randomblob(16))) AS queue_id,
                       j.id, j.company, j.title, j.location, j.source, j.url,
                       j.description, j.salary, j.employment_type, j.score,
                       j.status, j.notes
                FROM jobs AS j
                JOIN job_intelligence AS i ON i.job_url = j.url
                WHERE ({reason_sql}) = 'ACCEPTED'
                ORDER BY j.score DESC, j.company ASC, j.title ASC
                LIMIT ?
                """,
                (minimum_score, limit),
            ).fetchall()
        )
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            for row in rows:
                self.connection.execute(
                    """
                    INSERT INTO automation_queue_audit(
                        queue_id, job_id, stage, decision, reason, created_at
                    ) VALUES(?, ?, 'QUEUE_ENTRY', 'ACCEPTED', 'Eligible for automation', ?)
                    """,
                    (row['queue_id'], row['id'], now),
                )
        return rows

    def claim_application_run(
        self,
        job_id: int,
        idempotency_key: str,
        candidate_profile_hash: str,
        document_hash: str,
    ) -> tuple[sqlite3.Row, bool]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO application_runs(
                    job_id, idempotency_key, candidate_profile_hash,
                    document_hash, status, started_at, updated_at
                )
                VALUES(?, ?, ?, ?, 'CREATED', ?, ?)
                """,
                (
                    job_id,
                    idempotency_key,
                    candidate_profile_hash,
                    document_hash,
                    now,
                    now,
                ),
            )
        row = self.get_application_run(idempotency_key)
        if row is None:
            raise RuntimeError("Application run could not be claimed")
        return row, cursor.rowcount == 1

    def get_application_run(self, idempotency_key: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, job_id, idempotency_key, candidate_profile_hash,
                   document_hash, status, started_at, updated_at,
                   completed_at, confirmation_text, confirmation_url,
                   active_url, screenshot_path, last_error
            FROM application_runs
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()

    def update_application_run(
        self,
        idempotency_key: str,
        status: str,
        *,
        confirmation_text: str = "",
        confirmation_url: str = "",
        screenshot_path: str = "",
        last_error: str = "",
        active_url: str = "",
    ) -> sqlite3.Row:
        normalized = status.strip().upper()
        if normalized not in APPLICATION_RUN_STATUSES:
            raise ValueError(f"Unsupported application run status: {status}")

        current = self.get_application_run(idempotency_key)
        if current is None:
            raise ValueError("Application run not found")
        old_status = current["status"]
        allowed = APPLICATION_RUN_TRANSITIONS[old_status]
        if normalized != old_status and normalized not in allowed:
            raise ValueError(
                f"Invalid application run transition: {old_status} -> {normalized}"
            )

        now = datetime.now(timezone.utc).isoformat()
        terminal = {
            "READY_TO_REVIEW",
            "HUMAN_VERIFICATION",
            "MANUAL_REQUIRED",
            "CONFIRMED",
            "UNKNOWN",
            "FAILED",
            "BLOCKED",
        }
        completed_at = now if normalized in terminal else None
        with self.connection:
            self.connection.execute(
                """
                UPDATE application_runs
                SET status = ?, updated_at = ?,
                    completed_at = COALESCE(?, completed_at),
                    confirmation_text = CASE WHEN ? != '' THEN ? ELSE confirmation_text END,
                    confirmation_url = CASE WHEN ? != '' THEN ? ELSE confirmation_url END,
                    active_url = CASE WHEN ? != '' THEN ? ELSE active_url END,
                    screenshot_path = CASE WHEN ? != '' THEN ? ELSE screenshot_path END,
                    last_error = CASE WHEN ? != '' THEN ? ELSE last_error END
                WHERE idempotency_key = ?
                """,
                (
                    normalized,
                    now,
                    completed_at,
                    confirmation_text,
                    confirmation_text,
                    confirmation_url,
                    confirmation_url,
                    active_url,
                    active_url,
                    screenshot_path,
                    screenshot_path,
                    last_error,
                    last_error,
                    idempotency_key,
                ),
            )
        updated = self.get_application_run(idempotency_key)
        if updated is None:
            raise RuntimeError("Application run disappeared during update")
        return updated

    def record_automation_attempt(
        self,
        job_id: int,
        status: str,
        message: str,
        screenshot_path: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO automation_attempts(
                    job_id, status, message, screenshot_path, attempted_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    status.strip().upper(),
                    message.strip(),
                    screenshot_path.strip(),
                    now,
                ),
            )

    def claim_notification_delivery(
        self,
        job_id: int,
        dedup_key: str,
        auth_mode: str,
    ) -> tuple[sqlite3.Row, bool]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO notification_deliveries(
                    job_id, dedup_key, channel, auth_mode, status,
                    created_at, updated_at
                )
                VALUES(?, ?, 'EMAIL', ?, 'QUEUED', ?, ?)
                """,
                (job_id, dedup_key, auth_mode.strip().upper(), now, now),
            )
        row = self.get_notification_delivery(dedup_key)
        if row is None:
            raise RuntimeError("Notification delivery could not be claimed")
        if cursor.rowcount == 1:
            return row, True
        if row["status"] != "SENT":
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE notification_deliveries
                    SET status = 'QUEUED', auth_mode = ?, updated_at = ?
                    WHERE dedup_key = ? AND status != 'SENT'
                    """,
                    (auth_mode.strip().upper(), now, dedup_key),
                )
            refreshed = self.get_notification_delivery(dedup_key)
            if refreshed is None:
                raise RuntimeError("Notification delivery disappeared during retry claim")
            return refreshed, True
        return row, False

    def get_notification_delivery(self, dedup_key: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, job_id, dedup_key, channel, auth_mode, status,
                   attempt_count, last_error_code, outbox_path,
                   created_at, updated_at, sent_at
            FROM notification_deliveries
            WHERE dedup_key = ?
            """,
            (dedup_key,),
        ).fetchone()

    def update_notification_delivery(
        self,
        dedup_key: str,
        status: str,
        *,
        error_code: str = "",
        outbox_path: str = "",
    ) -> sqlite3.Row:
        normalized = status.strip().upper()
        if normalized not in NOTIFICATION_DELIVERY_STATUSES:
            raise ValueError(f"Unsupported notification status: {status}")
        current = self.get_notification_delivery(dedup_key)
        if current is None:
            raise ValueError("Notification delivery not found")
        if current["status"] == "SENT" and normalized != "SENT":
            raise ValueError("A sent notification cannot return to an earlier state")

        now = datetime.now(timezone.utc).isoformat()
        attempt_increment = 1 if normalized == "SENDING" else 0
        sent_at = now if normalized == "SENT" else None
        with self.connection:
            self.connection.execute(
                """
                UPDATE notification_deliveries
                SET status = ?,
                    attempt_count = attempt_count + ?,
                    last_error_code = ?,
                    outbox_path = CASE WHEN ? != '' THEN ? ELSE outbox_path END,
                    updated_at = ?,
                    sent_at = COALESCE(?, sent_at)
                WHERE dedup_key = ?
                """,
                (
                    normalized,
                    attempt_increment,
                    error_code.strip().upper(),
                    outbox_path,
                    outbox_path,
                    now,
                    sent_at,
                    dedup_key,
                ),
            )
        updated = self.get_notification_delivery(dedup_key)
        if updated is None:
            raise RuntimeError("Notification delivery disappeared during update")
        return updated

    def list_automation_attempts(
        self,
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT a.id, a.job_id, j.company, j.title, a.status,
                       a.message, a.screenshot_path, a.attempted_at
                FROM automation_attempts AS a
                JOIN jobs AS j ON j.id = a.job_id
                ORDER BY a.attempted_at DESC, a.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        )


    def upsert_job_intelligence(self, job_url: str, intelligence) -> None:
        now = datetime.now(timezone.utc).isoformat()
        job_row = self.connection.execute(
            "SELECT url FROM jobs WHERE canonical_url = ? LIMIT 1",
            (canonicalize_job_url(job_url),),
        ).fetchone()
        stored_job_url = job_row["url"] if job_row is not None else job_url
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO job_intelligence(
                    job_url, sponsorship_score, sponsorship_label,
                    relocation_label, international_hiring_label, confidence,
                    ngo_label, blocked, block_reason, block_category,
                    recommendation, assessed_at
                    , decision_verdict, decision_reason_codes,
                    decision_evidence, rule_version, primary_reason
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    sponsorship_score = excluded.sponsorship_score,
                    sponsorship_label = excluded.sponsorship_label,
                    relocation_label = excluded.relocation_label,
                    international_hiring_label = excluded.international_hiring_label,
                    confidence = excluded.confidence,
                    ngo_label = excluded.ngo_label,
                    blocked = excluded.blocked,
                    block_reason = excluded.block_reason,
                    block_category = excluded.block_category,
                    recommendation = excluded.recommendation,
                    decision_verdict = excluded.decision_verdict,
                    decision_reason_codes = excluded.decision_reason_codes,
                    decision_evidence = excluded.decision_evidence,
                    rule_version = excluded.rule_version,
                    primary_reason = excluded.primary_reason,
                    assessed_at = excluded.assessed_at
                """,
                (
                    stored_job_url,
                    intelligence.sponsorship_score,
                    intelligence.sponsorship_label,
                    intelligence.relocation_label,
                    intelligence.international_hiring_label,
                    intelligence.confidence,
                    intelligence.ngo_label,
                    int(intelligence.blocked),
                    intelligence.block_reason,
                    intelligence.block_category,
                    intelligence.recommendation,
                    now,
                    intelligence.decision_verdict,
                    json.dumps(intelligence.decision_reason_codes),
                    json.dumps(intelligence.decision_evidence),
                    intelligence.rule_version,
                    getattr(intelligence, 'primary_reason', ''),
                ),
            )

    def upsert_job_intelligence_batch(self, intelligence_by_url: dict[str, object]) -> None:
        if not intelligence_by_url:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for job_url, intelligence in intelligence_by_url.items():
            job_row = self.connection.execute(
                "SELECT url FROM jobs WHERE canonical_url = ? LIMIT 1",
                (canonicalize_job_url(job_url),),
            ).fetchone()
            stored_job_url = job_row["url"] if job_row is not None else job_url
            rows.append((
                stored_job_url,
                intelligence.sponsorship_score,
                intelligence.sponsorship_label,
                intelligence.relocation_label,
                intelligence.international_hiring_label,
                intelligence.confidence,
                intelligence.ngo_label,
                int(intelligence.blocked),
                intelligence.block_reason,
                intelligence.block_category,
                intelligence.recommendation,
                now,
                intelligence.decision_verdict,
                json.dumps(intelligence.decision_reason_codes),
                json.dumps(intelligence.decision_evidence),
                intelligence.rule_version,
                getattr(intelligence, 'primary_reason', ''),
            ))
        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO job_intelligence(
                    job_url, sponsorship_score, sponsorship_label,
                    relocation_label, international_hiring_label, confidence,
                    ngo_label, blocked, block_reason, block_category,
                    recommendation, assessed_at, decision_verdict,
                    decision_reason_codes, decision_evidence, rule_version,
                    primary_reason
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    sponsorship_score = excluded.sponsorship_score,
                    sponsorship_label = excluded.sponsorship_label,
                    relocation_label = excluded.relocation_label,
                    international_hiring_label = excluded.international_hiring_label,
                    confidence = excluded.confidence,
                    ngo_label = excluded.ngo_label,
                    blocked = excluded.blocked,
                    block_reason = excluded.block_reason,
                    block_category = excluded.block_category,
                    recommendation = excluded.recommendation,
                    decision_verdict = excluded.decision_verdict,
                    decision_reason_codes = excluded.decision_reason_codes,
                    decision_evidence = excluded.decision_evidence,
                    rule_version = excluded.rule_version,
                    primary_reason = excluded.primary_reason,
                    assessed_at = excluded.assessed_at
                """,
                rows,
            )

    def refresh_employer_memory(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO employer_memory(
                    company, applications, interviews, rejections, offers,
                    automation_attempts, automation_successes,
                    automation_success_rate, sponsorship_score,
                    last_contact, updated_at
                )
                SELECT
                    j.company,
                    SUM(CASE WHEN j.applied = 1 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN j.status = 'INTERVIEW' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN j.status = 'REJECTED' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN j.status = 'OFFER' THEN 1 ELSE 0 END),
                    COALESCE(a.attempts, 0),
                    COALESCE(a.successes, 0),
                    CASE WHEN COALESCE(a.attempts, 0) = 0 THEN 0.0
                         ELSE ROUND(a.successes * 100.0 / a.attempts, 1) END,
                    COALESCE(s.sponsorship_score, 0),
                    MAX(j.updated_at),
                    ?
                FROM jobs AS j
                LEFT JOIN (
                    SELECT j2.company, COUNT(*) AS attempts,
                           SUM(CASE WHEN aa.status IN ('AUTO_SUBMITTED', 'SUBMITTED')
                                    THEN 1 ELSE 0 END) AS successes
                    FROM automation_attempts AS aa
                    JOIN jobs AS j2 ON j2.id = aa.job_id
                    GROUP BY j2.company
                ) AS a ON a.company = j.company
                LEFT JOIN (
                    SELECT j3.company, MAX(ji.sponsorship_score) AS sponsorship_score
                    FROM jobs AS j3
                    JOIN job_intelligence AS ji ON ji.job_url = j3.url
                    GROUP BY j3.company
                ) AS s ON s.company = j.company
                GROUP BY j.company
                ON CONFLICT(company) DO UPDATE SET
                    applications = excluded.applications,
                    interviews = excluded.interviews,
                    rejections = excluded.rejections,
                    offers = excluded.offers,
                    automation_attempts = excluded.automation_attempts,
                    automation_successes = excluded.automation_successes,
                    automation_success_rate = excluded.automation_success_rate,
                    sponsorship_score = excluded.sponsorship_score,
                    last_contact = excluded.last_contact,
                    updated_at = excluded.updated_at
                """,
                (now,),
            )

    def mission_briefing(self, minimum_score: int) -> dict[str, object]:
        queueable = """
            j.score >= ?
            AND j.status IN ('NEW', 'SHORTLISTED', 'PREPARING')
            AND COALESCE(i.blocked, 0) = 0
            AND i.decision_verdict IN ('PRIORITY', 'APPLY')
            AND NOT EXISTS (
                SELECT 1 FROM automation_attempts a
                WHERE a.job_id = j.id
                  AND a.status IN ('AUTO_SUBMITTED', 'READY_TO_REVIEW',
                                   'HUMAN_VERIFICATION', 'SUBMITTED',
                                   'MANUAL_REQUIRED')
            )
            AND NOT EXISTS (
                SELECT 1 FROM application_runs r WHERE r.job_id = j.id
            )
        """
        counts = self.connection.execute(
            f"""
            SELECT
                COUNT(*) AS new_jobs,
                SUM(CASE WHEN ({queueable}) AND i.recommendation = 'PRIORITY'
                         THEN 1 ELSE 0 END) AS priority_jobs,
                SUM(CASE WHEN ({queueable}) AND i.recommendation = 'APPLY'
                         THEN 1 ELSE 0 END) AS apply_jobs,
                SUM(CASE WHEN i.ngo_label != 'CORPORATE' THEN 1 ELSE 0 END)
                    AS ngo_jobs,
                SUM(CASE WHEN i.sponsorship_label IN ('YES', 'POSSIBLE')
                         THEN 1 ELSE 0 END) AS visa_jobs,
                SUM(CASE WHEN i.blocked = 1 THEN 1 ELSE 0 END) AS blocked_jobs
            FROM jobs AS j
            LEFT JOIN job_intelligence AS i ON i.job_url = j.url
            WHERE j.score >= ?
            """,
            (minimum_score, minimum_score, minimum_score),
        ).fetchone()

        manual = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM automation_attempts
            WHERE status IN ('READY_TO_REVIEW', 'HUMAN_VERIFICATION',
                             'MANUAL_REQUIRED')
            """
        ).fetchone()

        targets = list(
            self.connection.execute(
                f"""
                SELECT j.company, j.title, j.score,
                       COALESCE(i.sponsorship_label, 'UNKNOWN')
                           AS sponsorship_label,
                       COALESCE(i.recommendation, 'APPLY') AS recommendation
                FROM jobs AS j
                JOIN job_intelligence AS i ON i.job_url = j.url
                WHERE {queueable}
                ORDER BY
                    CASE i.recommendation WHEN 'PRIORITY' THEN 1 ELSE 2 END,
                    j.score DESC
                LIMIT 5
                """,
                (minimum_score,),
            ).fetchall()
        )

        return {
            "new_jobs": int(counts["new_jobs"] or 0),
            "priority_jobs": int(counts["priority_jobs"] or 0),
            "apply_jobs": int(counts["apply_jobs"] or 0),
            "ngo_jobs": int(counts["ngo_jobs"] or 0),
            "visa_jobs": int(counts["visa_jobs"] or 0),
            "blocked_jobs": int(counts["blocked_jobs"] or 0),
            "manual_review": int(manual["count"] or 0),
            "top_targets": targets,
        }

    def list_employer_memory(self, limit: int = 25) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT company, applications, interviews, rejections, offers,
                       automation_attempts, automation_successes,
                       automation_success_rate, sponsorship_score, last_contact
                FROM employer_memory
                ORDER BY offers DESC, interviews DESC,
                         sponsorship_score DESC, applications DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        )

    def queue_human_action(self, job_id: int, status: str, reason: str, job_score: int, opportunity_score: int, email_status: str = "", email_location: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO human_action_queue(job_id,status,reason,job_score,opportunity_score,email_status,email_location,queued_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status, reason=excluded.reason,
                    job_score=excluded.job_score, opportunity_score=excluded.opportunity_score,
                    email_status=excluded.email_status, email_location=excluded.email_location,
                    queued_at=excluded.queued_at, resolved_at=NULL, resolution_notes=''
                """,
                (job_id,status.strip().upper(),reason.strip(),int(job_score),int(opportunity_score),email_status.strip().upper(),email_location.strip(),now),
            )

    def resolve_human_action(self, job_id: int, resolution_notes: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "UPDATE human_action_queue SET resolved_at=?, resolution_notes=? WHERE job_id=?",
                (now,resolution_notes.strip(),job_id),
            )

    def list_human_action_queue(self, unresolved_only: bool = True, limit: int = 100) -> list[sqlite3.Row]:
        where = "WHERE q.resolved_at IS NULL" if unresolved_only else ""
        return list(self.connection.execute(
            f"""
            SELECT q.*, j.company, j.title, j.location, j.url, j.source,
                   COALESCE(i.sponsorship_label,'UNKNOWN') AS sponsorship_label,
                   COALESCE(i.relocation_label,'UNKNOWN') AS relocation_label,
                   COALESCE(i.recommendation,'APPLY') AS recommendation
            FROM human_action_queue q
            JOIN jobs j ON j.id=q.job_id
            LEFT JOIN job_intelligence i ON i.job_url=j.url
            {where}
            ORDER BY q.opportunity_score DESC, q.job_score DESC, q.queued_at ASC
            LIMIT ?
            """,(limit,)).fetchall())

    def operational_briefing(self) -> dict[str, object]:
        a=self.connection.execute("SELECT SUM(CASE WHEN applied=1 THEN 1 ELSE 0 END) completed, SUM(CASE WHEN status='INTERVIEW' THEN 1 ELSE 0 END) interviews, SUM(CASE WHEN status='OFFER' THEN 1 ELSE 0 END) offers FROM jobs").fetchone()
        q=self.connection.execute("SELECT COUNT(*) waiting, SUM(CASE WHEN status='HUMAN_VERIFICATION' THEN 1 ELSE 0 END) verification, SUM(CASE WHEN status='READY_TO_REVIEW' THEN 1 ELSE 0 END) review, SUM(CASE WHEN email_status='SENT' THEN 1 ELSE 0 END) emailed FROM human_action_queue WHERE resolved_at IS NULL").fetchone()
        i=self.connection.execute("SELECT SUM(CASE WHEN sponsorship_label IN ('YES','POSSIBLE') THEN 1 ELSE 0 END) sponsor_jobs, SUM(CASE WHEN ngo_label!='CORPORATE' THEN 1 ELSE 0 END) ngo_jobs FROM job_intelligence").fetchone()
        waiting=int(q['waiting'] or 0)
        return {'completed':int(a['completed'] or 0),'interviews':int(a['interviews'] or 0),'offers':int(a['offers'] or 0),'waiting':waiting,'verification':int(q['verification'] or 0),'review':int(q['review'] or 0),'emailed':int(q['emailed'] or 0),'sponsor_jobs':int(i['sponsor_jobs'] or 0),'ngo_jobs':int(i['ngo_jobs'] or 0),'estimated_review_minutes':waiting*3,'top_queue':self.list_human_action_queue(True,5)}

    def close(self) -> None:
        self.connection.close()
