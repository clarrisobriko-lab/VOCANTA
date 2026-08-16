from __future__ import annotations

from core.database import Database
from automation.inbox_ingestion import process_inbox_messages


def normalize_mail_message(message: dict) -> dict:
    return {
        "id": str(message.get("id",message.get("message_id",""))),
        "from": str(message.get("from",message.get("sender",""))),
        "subject": str(message.get("subject","")),
        "body": str(message.get("body",message.get("text",message.get("snippet","")))),
        "date": str(message.get("date",message.get("received_at",""))),
    }


def run_inbox_runtime(messages, *, database=None):
    owns_database=database is None
    database=database or Database()
    try:
        normalized=[normalize_mail_message(message) for message in messages]
        return process_inbox_messages(database.connection,normalized)
    finally:
        if owns_database: database.close()


def summarize_inbox_results(results) -> dict[str,int]:
    summary={"processed":0,"duplicate":0,"unmatched":0,"invalid":0}
    for result in results:
        key=result.status.lower()
        if key in summary: summary[key]+=1
    return summary
