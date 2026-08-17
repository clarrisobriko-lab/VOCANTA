import sqlite3

from core.employer_reply_store import ensure_reply_schema


def _plan(connection, sql, params=()):
    return ' '.join(str(row[3]) for row in connection.execute('EXPLAIN QUERY PLAN '+sql, params).fetchall())


def test_active_reply_query_uses_status_archive_created_index():
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    plan=_plan(connection,"SELECT message_id FROM employer_reply_drafts WHERE status=? AND archived_at IS NULL ORDER BY created_at DESC LIMIT 10",('APPROVED',))
    assert 'idx_reply_status_archive_created' in plan


def test_sent_reply_query_uses_status_archive_sent_index():
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    plan=_plan(connection,"SELECT message_id FROM employer_reply_drafts WHERE status='SENT' AND archived_at IS NULL ORDER BY sent_at DESC LIMIT 10")
    assert 'idx_reply_status_archive_sent' in plan


def test_stale_send_query_uses_status_claim_index():
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    plan=_plan(connection,"SELECT message_id FROM employer_reply_drafts WHERE status='SENDING' AND send_claimed_at<=?",('2026-08-17T00:00:00+00:00',))
    assert 'idx_reply_status_claim' in plan


def test_reply_audit_lookup_uses_message_index():
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    plan=_plan(connection,"SELECT event FROM employer_reply_audit WHERE message_id=? ORDER BY id DESC LIMIT 20",('m1',))
    assert 'idx_reply_audit_message_id' in plan
