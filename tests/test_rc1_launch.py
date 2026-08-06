from pathlib import Path

import pytest

from config import settings
from core.database import Database
from retry_last_unconfirmed import authorize_retry, latest_retryable_job


def seed_job(database: Database, *, applied: int = 0) -> int:
    with database.connection:
        cursor = database.connection.execute(
            """
            INSERT INTO jobs(
                company, title, location, source, url, canonical_url,
                description, salary, employment_type, score, status, applied,
                notes, first_seen_at, last_seen_at, updated_at
            ) VALUES(
                'Canonical', 'Executive Assistant', 'Home based - EMEA',
                'Greenhouse', 'https://job-boards.greenhouse.io/canonical/jobs/123',
                'https://job-boards.greenhouse.io/canonical/jobs/123', '', '', '',
                100, 'NEW', ?, '', '2026-07-29T00:00:00+00:00',
                '2026-07-29T00:00:00+00:00', '2026-07-29T00:00:00+00:00'
            )
            """,
            (applied,),
        )
    return int(cursor.lastrowid)


def seed_run(database: Database, job_id: int, status: str, confirmation: str = '') -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO application_runs(
                job_id, idempotency_key, candidate_profile_hash, document_hash,
                status, started_at, updated_at, confirmation_text,
                confirmation_url, active_url, screenshot_path, last_error
            ) VALUES(?, 'key', 'profile', 'docs', ?, '2026-07-29T00:00:00+00:00',
                     '2026-07-29T00:01:00+00:00', ?, '', '', '', '')
            """,
            (job_id, status, confirmation),
        )
        database.connection.execute(
            """
            INSERT INTO automation_attempts(job_id, status, message, screenshot_path, attempted_at)
            VALUES(?, ?, 'test', '', '2026-07-29T00:01:00+00:00')
            """,
            (job_id, status),
        )


def test_rc1_uses_deterministic_post_discovery_automation():
    assert settings.APP_VERSION == '3.3.0'
    assert settings.APP_RELEASE == '3.3'
    assert settings.STREAM_AUTOMATION_ON_DISCOVERY is False
    assert settings.AUTOMATION_MAX_APPLICATIONS_PER_RUN == 1
    assert settings.SUPPORTED_AUTOMATION_ATS == {'GREENHOUSE'}


def test_safe_retry_clears_only_unconfirmed_state(tmp_path: Path):
    database = Database(tmp_path / 'vocanta.db')
    try:
        job_id = seed_job(database)
        seed_run(database, job_id, 'MANUAL_REQUIRED')
        assert latest_retryable_job(database)['id'] == job_id

        authorize_retry(database, job_id)

        job = database.connection.execute('SELECT status, applied FROM jobs WHERE id = ?', (job_id,)).fetchone()
        assert job['status'] == 'NEW'
        assert job['applied'] == 0
        assert database.connection.execute('SELECT COUNT(*) FROM application_runs WHERE job_id = ?', (job_id,)).fetchone()[0] == 0
        assert database.connection.execute('SELECT COUNT(*) FROM automation_attempts WHERE job_id = ?', (job_id,)).fetchone()[0] == 0
        audit = database.connection.execute(
            "SELECT decision, reason FROM automation_queue_audit WHERE job_id = ? AND stage = 'SAFE_RETRY'",
            (job_id,),
        ).fetchone()
        assert audit['decision'] == 'ACCEPTED'
        assert 'MANUAL_REQUIRED' in audit['reason']
    finally:
        database.close()


def test_safe_retry_refuses_confirmed_evidence(tmp_path: Path):
    database = Database(tmp_path / 'vocanta.db')
    try:
        job_id = seed_job(database)
        seed_run(database, job_id, 'CONFIRMED', 'Thank you for applying')
        with pytest.raises(ValueError, match='submission evidence'):
            authorize_retry(database, job_id)
    finally:
        database.close()


def test_safe_retry_refuses_applied_job(tmp_path: Path):
    database = Database(tmp_path / 'vocanta.db')
    try:
        job_id = seed_job(database, applied=1)
        seed_run(database, job_id, 'FAILED')
        with pytest.raises(ValueError, match='already marked applied'):
            authorize_retry(database, job_id)
    finally:
        database.close()
