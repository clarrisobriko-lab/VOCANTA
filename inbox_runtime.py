from __future__ import annotations

from core.database import Database
from automation.gmail_auth import build_gmail_service
from automation.gmail_source import GmailInboxSource
from automation.inbox_ingestion import process_inbox_messages


def normalize_mail_message(message: dict) -> dict:
    return {"id":str(message.get("id",message.get("message_id",""))),"from":str(message.get("from",message.get("sender",""))),"subject":str(message.get("subject","")),"body":str(message.get("body",message.get("text",message.get("snippet","")))),"date":str(message.get("date",message.get("received_at","")))}


def run_inbox_runtime(messages, *, database=None):
    owns_database=database is None; database=database or Database()
    try: return process_inbox_messages(database.connection,[normalize_mail_message(message) for message in messages])
    finally:
        if owns_database: database.close()


def run_gmail_inbox_runtime(*, database=None, service=None, query="in:inbox newer_than:30d", limit=100):
    service=service or build_gmail_service()
    messages=GmailInboxSource(service).fetch_recent(query=query,limit=limit)
    return run_inbox_runtime(messages,database=database)


def summarize_inbox_results(results) -> dict[str,int]:
    summary={"processed":0,"duplicate":0,"unmatched":0,"invalid":0}
    for result in results:
        key=result.status.lower()
        if key in summary: summary[key]+=1
    return summary


def main() -> int:
    try: results=run_gmail_inbox_runtime()
    except RuntimeError as exc:
        print(f"VOCANTA inbox runtime skipped: {exc}"); return 0
    summary=summarize_inbox_results(results)
    print("VOCANTA inbox runtime: "+", ".join(f"{value} {key}" for key,value in summary.items()))
    return 0


if __name__=="__main__": raise SystemExit(main())
