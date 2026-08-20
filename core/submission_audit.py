from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def ensure_submission_evidence_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS submission_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            application_run_id INTEGER,
            evidence_path TEXT NOT NULL,
            package_sha256 TEXT NOT NULL,
            ats TEXT NOT NULL DEFAULT '',
            outcome TEXT NOT NULL DEFAULT '',
            confirmation_url TEXT NOT NULL DEFAULT '',
            screenshot_path TEXT NOT NULL DEFAULT '',
            recorded_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(application_run_id) REFERENCES application_runs(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submission_evidence_job ON submission_evidence(job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submission_evidence_run ON submission_evidence(application_run_id)")


def record_submission_evidence(
    connection: sqlite3.Connection,
    *,
    job_id: int,
    evidence_path: Path | str,
    package_sha256: str,
    ats: str,
    outcome: str,
    confirmation_url: str = "",
    screenshot_path: str = "",
    application_run_id: int | None = None,
) -> int:
    ensure_submission_evidence_schema(connection)
    cursor = connection.execute(
        """
        INSERT INTO submission_evidence(
            job_id, application_run_id, evidence_path, package_sha256, ats,
            outcome, confirmation_url, screenshot_path, recorded_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id, application_run_id, str(evidence_path), package_sha256,
            ats.strip().upper(), outcome.strip().upper(), confirmation_url.strip(),
            screenshot_path.strip(), datetime.now(timezone.utc).isoformat(),
        ),
    )
    return int(cursor.lastrowid)


def list_submission_evidence(connection: sqlite3.Connection, job_id: int) -> list[sqlite3.Row]:
    ensure_submission_evidence_schema(connection)
    return list(connection.execute(
        """
        SELECT id, job_id, application_run_id, evidence_path, package_sha256,
               ats, outcome, confirmation_url, screenshot_path, recorded_at
        FROM submission_evidence
        WHERE job_id = ?
        ORDER BY recorded_at DESC, id DESC
        """,
        (job_id,),
    ).fetchall())
