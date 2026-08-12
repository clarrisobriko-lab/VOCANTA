import json
from datetime import datetime, timezone

from agents.scorer import ApplicationDecision
from core.database import Database


SUBMITTED_STATUSES = {"AUTO_SUBMITTED", "SUBMITTED", "CONFIRMED"}
HUMAN_STATUSES = {"READY_TO_REVIEW", "HUMAN_VERIFICATION", "MANUAL_REQUIRED"}


class AcquisitionAuditStore:
    """Durable ATS acquisition decision and runtime outcome history."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.database.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS acquisition_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                composite_score INTEGER NOT NULL,
                base_score INTEGER NOT NULL,
                ats_score INTEGER NOT NULL,
                should_apply INTEGER NOT NULL,
                matched_skills TEXT NOT NULL DEFAULT '[]',
                missing_skills TEXT NOT NULL DEFAULT '[]',
                reason TEXT NOT NULL DEFAULT '',
                package_path TEXT NOT NULL DEFAULT '',
                automation_status TEXT NOT NULL DEFAULT '',
                decided_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        columns = {row["name"] for row in self.database.connection.execute("PRAGMA table_info(acquisition_decisions)").fetchall()}
        if "package_path" not in columns:
            self.database.connection.execute("ALTER TABLE acquisition_decisions ADD COLUMN package_path TEXT NOT NULL DEFAULT ''")
        if "automation_status" not in columns:
            self.database.connection.execute("ALTER TABLE acquisition_decisions ADD COLUMN automation_status TEXT NOT NULL DEFAULT ''")
        self.database.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_acquisition_decisions_job ON acquisition_decisions(job_id, decided_at DESC)"
        )
        self.database.connection.commit()

    def record(self, job_id: int, decision: ApplicationDecision, *, package_path: str = "", automation_status: str = "") -> int:
        if self.database.get_job(job_id) is None:
            raise ValueError("Job not found")
        with self.database.connection:
            cursor = self.database.connection.execute(
                """
                INSERT INTO acquisition_decisions(
                    job_id, composite_score, base_score, ats_score, should_apply,
                    matched_skills, missing_skills, reason, package_path,
                    automation_status, decided_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, decision.score, decision.base_score, decision.ats_score,
                 int(decision.should_apply), json.dumps(decision.matched_skills),
                 json.dumps(decision.missing_skills), decision.reason,
                 package_path, automation_status.strip().upper(),
                 datetime.now(timezone.utc).isoformat()),
            )
        return int(cursor.lastrowid)

    def latest(self, job_id: int) -> dict[str, object] | None:
        row = self.database.connection.execute(
            "SELECT * FROM acquisition_decisions WHERE job_id = ? ORDER BY decided_at DESC, id DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if row is None: return None
        result = dict(row); result["should_apply"] = bool(result["should_apply"])
        result["matched_skills"] = tuple(json.loads(str(result["matched_skills"])))
        result["missing_skills"] = tuple(json.loads(str(result["missing_skills"])))
        return result

    def history(self, job_id: int) -> list[dict[str, object]]:
        rows = self.database.connection.execute(
            "SELECT * FROM acquisition_decisions WHERE job_id = ? ORDER BY decided_at DESC, id DESC", (job_id,)
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row); item["should_apply"] = bool(item["should_apply"])
            item["matched_skills"] = tuple(json.loads(str(item["matched_skills"])))
            item["missing_skills"] = tuple(json.loads(str(item["missing_skills"])))
            results.append(item)
        return results


def reconcile_application_outcome(database: Database, job_id: int, automation) -> str:
    """Count only evidenced submissions as applications; preserve retryability otherwise."""
    status = automation.status.strip().upper()
    message = automation.message.strip()
    if status in SUBMITTED_STATUSES:
        database.update_application(job_id, "APPLIED", notes=message)
        return "APPLIED"
    if status in HUMAN_STATUSES:
        database.update_application(job_id, "PREPARING", notes=message)
        return "PREPARING"
    current = database.get_job(job_id)
    if current is not None and current["status"] == "PREPARING":
        database.update_application(job_id, "NEW", notes=message)
    refreshed = database.get_job(job_id)
    return refreshed["status"] if refreshed is not None else "NEW"
