from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from core.follow_up_store import cancel_job_follow_ups
from intelligence.employer_responses import EmployerResponse

STATUS_MAP={"OFFER":"OFFER","INTERVIEW":"INTERVIEW","REJECTED":"REJECTED"}


def ensure_response_schema(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS employer_responses(message_id TEXT PRIMARY KEY,job_id INTEGER NOT NULL,sender TEXT NOT NULL DEFAULT '',subject TEXT NOT NULL DEFAULT '',classification TEXT NOT NULL,confidence INTEGER NOT NULL,reason TEXT NOT NULL DEFAULT '',received_at TEXT NOT NULL,processed_at TEXT NOT NULL,thread_id TEXT NOT NULL DEFAULT '',internet_message_id TEXT NOT NULL DEFAULT '',references_header TEXT NOT NULL DEFAULT '',FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)")
    columns={r[1] for r in connection.execute("PRAGMA table_info(employer_responses)").fetchall()}
    for name in ('thread_id','internet_message_id','references_header'):
        if name not in columns: connection.execute(f"ALTER TABLE employer_responses ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
    connection.commit()


def record_employer_response(connection: sqlite3.Connection,job_id: int,message_id: str,sender: str,subject: str,response: EmployerResponse,*,received_at: str="",thread_id: str="",internet_message_id: str="",references_header: str="",now=None) -> bool:
    ensure_response_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    cursor=connection.execute("INSERT OR IGNORE INTO employer_responses(message_id,job_id,sender,subject,classification,confidence,reason,received_at,processed_at,thread_id,internet_message_id,references_header) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(message_id,job_id,sender,subject,response.status,response.confidence,response.reason,received_at or stamp,stamp,thread_id,internet_message_id,references_header))
    if cursor.rowcount==0: connection.commit(); return False
    new_status=STATUS_MAP.get(response.status)
    if new_status:
        row=connection.execute("SELECT status FROM jobs WHERE id=?",(job_id,)).fetchone()
        if row is not None:
            old_status=str(row[0]); connection.execute("UPDATE jobs SET status=?,updated_at=? WHERE id=?",(new_status,stamp,job_id)); connection.execute("INSERT INTO application_history(job_id,old_status,new_status,notes,changed_at) VALUES(?,?,?,?,?)",(job_id,old_status,new_status,f"Employer response: {response.reason}",stamp)); cancel_job_follow_ups(connection,job_id)
    connection.commit(); return True
