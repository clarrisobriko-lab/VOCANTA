from __future__ import annotations

import os

from core.database import Database
from core.employer_reply_store import apply_reply_retention
from automation.email_transport import SMTPAlertSender
from automation.gmail_auth import build_gmail_service
from automation.gmail_source import GmailInboxSource
from automation.inbox_ingestion import process_inbox_messages
from automation.response_notification_runtime import notify_processed_responses


def normalize_mail_message(message: dict) -> dict:
    return {"id":str(message.get("id",message.get("message_id",""))),"from":str(message.get("from",message.get("sender",""))),"subject":str(message.get("subject","")),"body":str(message.get("body",message.get("text",message.get("snippet","")))),"date":str(message.get("date",message.get("received_at","")))}


def build_alert_sender_from_environment():
    host=os.getenv("VOCANTA_SMTP_HOST","").strip()
    username=os.getenv("VOCANTA_SMTP_USERNAME","").strip()
    password=os.getenv("VOCANTA_SMTP_PASSWORD","")
    recipient=os.getenv("VOCANTA_ALERT_RECIPIENT","").strip()
    if not host or not username or not password or not recipient: return None
    port=int((os.getenv("VOCANTA_SMTP_PORT","").strip() or "587"))
    from_address=os.getenv("VOCANTA_SMTP_FROM",username).strip() or username
    use_tls=os.getenv("VOCANTA_SMTP_TLS","1").strip().lower() not in {"0","false","no"}
    return SMTPAlertSender(host,port,username,password,recipient,from_address,use_tls=use_tls)


def run_inbox_runtime(messages, *, database=None, alert_sender=None):
    owns_database=database is None; database=database or Database()
    try:
        apply_reply_retention(database.connection)
        results=process_inbox_messages(database.connection,[normalize_mail_message(message) for message in messages])
        if alert_sender is not None: notify_processed_responses(database.connection,results,alert_sender)
        return results
    finally:
        if owns_database: database.close()


def run_gmail_inbox_runtime(*, database=None, service=None, alert_sender=None, query="in:inbox newer_than:30d", limit=100):
    service=service or build_gmail_service()
    messages=GmailInboxSource(service).fetch_recent(query=query,limit=limit)
    return run_inbox_runtime(messages,database=database,alert_sender=alert_sender)


def summarize_inbox_results(results) -> dict[str,int]:
    summary={"processed":0,"duplicate":0,"unmatched":0,"invalid":0}
    for result in results:
        key=result.status.lower()
        if key in summary: summary[key]+=1
    return summary


def main() -> int:
    try: results=run_gmail_inbox_runtime(alert_sender=build_alert_sender_from_environment())
    except RuntimeError as exc:
        print(f"VOCANTA inbox runtime skipped: {exc}"); return 0
    summary=summarize_inbox_results(results)
    print("VOCANTA inbox runtime: "+", ".join(f"{value} {key}" for key,value in summary.items()))
    return 0


if __name__=="__main__": raise SystemExit(main())
