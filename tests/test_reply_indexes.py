import sqlite3

from core.employer_reply_store import ensure_reply_schema


def test_reply_schema_creates_operational_indexes():
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    draft_indexes={row[1] for row in connection.execute("PRAGMA index_list('employer_reply_drafts')").fetchall()}
    audit_indexes={row[1] for row in connection.execute("PRAGMA index_list('employer_reply_audit')").fetchall()}
    assert 'idx_reply_status_archive_created' in draft_indexes
    assert 'idx_reply_status_archive_sent' in draft_indexes
    assert 'idx_reply_status_claim' in draft_indexes
    assert 'idx_reply_job' in draft_indexes
    assert 'idx_reply_gmail_message' in draft_indexes
    assert 'idx_reply_audit_message_id' in audit_indexes
    assert 'idx_reply_audit_created' in audit_indexes
