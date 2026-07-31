from agents.scorer import Scorer
from core.models import Job
from intelligence.assessment import assess_job
from intelligence.eligibility import assess_eligibility, production_block_reason


def revalidate_existing_jobs(database) -> dict[str, int]:
    scorer = Scorer()
    rows = database.connection.execute(
        """
        SELECT id, company, title, location, source, url, description,
               salary, employment_type, score, status
        FROM jobs
        WHERE status IN ('NEW', 'SHORTLISTED', 'PREPARING', 'REJECTED')
        """
    ).fetchall()
    blocked = 0
    restored = 0
    rescored = 0
    for row in rows:
        job = Job(
            company=row['company'], title=row['title'], location=row['location'],
            source=row['source'], url=row['url'], description=row['description'] or '',
            salary=row['salary'] or '', employment_type=row['employment_type'] or '',
            score=int(row['score'] or 0),
        )
        decision = assess_eligibility(job)
        intelligence = assess_job(job)
        database.upsert_job_intelligence(job.url, intelligence)
        new_score = scorer.score(job)
        production_reason = production_block_reason(job)
        if production_reason:
            new_status = 'REJECTED'
            blocked += 1
        else:
            new_status = 'NEW' if row['status'] == 'REJECTED' else row['status']
            restored += int(row['status'] == 'REJECTED')
        if new_score != int(row['score'] or 0) or new_status != row['status']:
            database.connection.execute(
                "UPDATE jobs SET score = ?, status = ?, notes = ? WHERE id = ?",
                (new_score, new_status, production_reason or '', row['id']),
            )
            rescored += 1
    # Close any stale human-action items for jobs that are no longer eligible.
    database.connection.execute(
        """
        UPDATE human_action_queue
        SET resolved_at = COALESCE(resolved_at, CURRENT_TIMESTAMP)
        WHERE resolved_at IS NULL
          AND job_id IN (SELECT id FROM jobs WHERE status = 'REJECTED')
        """
    )
    # Purge legacy discovery records that fail the current production rules.
    # Preserve genuine application history, interviews, rejections and offers.
    purge_candidates = database.connection.execute(
        """
        SELECT id FROM jobs
        WHERE status IN ('NEW', 'SHORTLISTED', 'PREPARING', 'REJECTED')
          AND applied = 0
        """
    ).fetchall()
    purged = 0
    for candidate in purge_candidates:
        current = database.get_job(candidate['id'])
        if current is None:
            continue
        job = Job(
            company=current['company'], title=current['title'],
            location=current['location'], source=current['source'],
            url=current['url'], description=current['description'] or '',
            salary=current['salary'] or '',
            employment_type=current['employment_type'] or '',
            score=int(current['score'] or 0),
        )
        if production_block_reason(job):
            queued = database.connection.execute('SELECT 1 FROM human_action_queue WHERE job_id = ?', (candidate['id'],)).fetchone()
            if queued is not None:
                continue
            database.connection.execute('DELETE FROM jobs WHERE id = ?', (candidate['id'],))
            database.connection.execute('DELETE FROM job_intelligence WHERE job_url = ?', (job.url,))
            purged += 1
    database.connection.commit()
    return {'checked': len(rows), 'blocked': blocked, 'restored': restored, 'rescored': rescored, 'purged': purged}
