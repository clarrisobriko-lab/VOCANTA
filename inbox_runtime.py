from __future__ import annotations

import os

from config.settings import REPLY_RETENTION_ALERT_THRESHOLD
from core.database import Database
from core.employer_reply_store import apply_reply_retention, ensure_reply_schema, mark_retention_alerted, retention_alert_seen
from automation.email_transport import SMTPAlertSender
from automation.gmail_auth import build_gmail_service
from automation.gmail_source import GmailInboxSource
from automation.inbox_ingestion import process_inbox_messages
from automation.response_notification_runtime import notify_processed_responses

RETENTION_ANOMALY_BASELINE_RUNS=20
RETENTION_ANOMALY_MIN_RUNS=5
RETENTION_ANOMALY_SIGMA=3.0


def normalize_mail_message(message: dict) -> dict:
    return {"id":str(message.get("id",message.get("message_id",""))),"from":str(message.get("from",message.get("sender",""))),"subject":str(message.get("subject","")),"body":str(message.get("body",message.get("text",message.get("snippet","")))),"date":str(message.get("date",message.get("received_at","")))}

def build_alert_sender_from_environment():
    host=os.getenv("VOCANTA_SMTP_HOST","").strip(); username=os.getenv("VOCANTA_SMTP_USERNAME","").strip(); password=os.getenv("VOCANTA_SMTP_PASSWORD",""); recipient=os.getenv("VOCANTA_ALERT_RECIPIENT","").strip()
    if not host or not username or not password or not recipient: return None
    port=int((os.getenv("VOCANTA_SMTP_PORT","").strip() or "587")); from_address=os.getenv("VOCANTA_SMTP_FROM",username).strip() or username; use_tls=os.getenv("VOCANTA_SMTP_TLS","1").strip().lower() not in {"0","false","no"}
    return SMTPAlertSender(host,port,username,password,recipient,from_address,use_tls=use_tls)
def retention_volume(retention: dict) -> int: return int(retention.get('archived_replies',0))+int(retention.get('audit_events',0))
def retention_alert_required(retention: dict,threshold=REPLY_RETENTION_ALERT_THRESHOLD) -> bool: return retention_volume(retention)>=max(1,int(threshold))
def retention_baseline(connection,limit=RETENTION_ANOMALY_BASELINE_RUNS):
    ensure_reply_schema(connection); rows=connection.execute("SELECT archived_replies+audit_events FROM employer_reply_retention_runs ORDER BY id DESC LIMIT ? OFFSET 1",(max(1,int(limit)),)).fetchall(); values=[int(row[0]) for row in rows]
    if not values: return {'runs':0,'mean':0.0,'deviation':0.0,'threshold':0.0}
    average=sum(values)/len(values); deviation=(sum((value-average)**2 for value in values)/len(values))**0.5 if len(values)>1 else 0.0; threshold=average+RETENTION_ANOMALY_SIGMA*deviation
    return {'runs':len(values),'mean':round(average,2),'deviation':round(deviation,2),'threshold':round(threshold,2)}
def retention_anomaly(connection,retention,min_runs=RETENTION_ANOMALY_MIN_RUNS):
    baseline=retention_baseline(connection); volume=retention_volume(retention); required=max(2,int(min_runs)); anomalous=baseline['runs']>=required and volume>baseline['threshold'] and volume>baseline['mean']
    return {'anomalous':anomalous,'volume':volume,**baseline}
def notify_retention_volume(retention: dict,alert_sender,threshold=REPLY_RETENTION_ALERT_THRESHOLD,connection=None) -> bool:
    anomaly=retention_anomaly(connection,retention) if connection is not None else {'anomalous':False,'runs':0,'mean':0.0,'deviation':0.0,'threshold':0.0,'volume':retention_volume(retention)}
    absolute=retention_alert_required(retention,threshold)
    if alert_sender is None or not (absolute or anomaly['anomalous']): return False
    signature=dict(retention); signature['audit_events']=int(retention.get('audit_events',0))+(1000000000 if anomaly['anomalous'] else 0)
    if connection is not None and retention_alert_seen(connection,signature): return False
    reason='historical anomaly' if anomaly['anomalous'] and not absolute else ('volume threshold and historical anomaly' if anomaly['anomalous'] else 'volume threshold')
    subject='VOCANTA retention volume alert'; body=f"Retention removed {retention.get('archived_replies',0)} archived replies and {retention.get('audit_events',0)} audit events. Total removed: {retention_volume(retention)}. Trigger: {reason}. Absolute threshold: {max(1,int(threshold))}. Baseline: {anomaly['runs']} prior runs, mean {anomaly['mean']}, deviation {anomaly['deviation']}, anomaly threshold {anomaly['threshold']}."
    try:
        alert_sender.send(subject,body)
        if connection is not None: mark_retention_alerted(connection,signature)
        return True
    except Exception as exc: print(f"VOCANTA retention alert failed: {exc}"); return False
def run_inbox_runtime(messages, *, database=None, alert_sender=None, retention_report=None):
    owns_database=database is None; database=database or Database()
    try:
        retention=apply_reply_retention(database.connection)
        if retention_report is not None: retention_report.update(retention)
        notify_retention_volume(retention,alert_sender,connection=database.connection)
        results=process_inbox_messages(database.connection,[normalize_mail_message(message) for message in messages])
        if alert_sender is not None: notify_processed_responses(database.connection,results,alert_sender)
        return results
    finally:
        if owns_database: database.close()
def run_gmail_inbox_runtime(*, database=None, service=None, alert_sender=None, query="in:inbox newer_than:30d", limit=100, retention_report=None):
    service=service or build_gmail_service(); messages=GmailInboxSource(service).fetch_recent(query=query,limit=limit); return run_inbox_runtime(messages,database=database,alert_sender=alert_sender,retention_report=retention_report)
def summarize_inbox_results(results) -> dict[str,int]:
    summary={"processed":0,"duplicate":0,"unmatched":0,"invalid":0}
    for result in results:
        key=result.status.lower()
        if key in summary: summary[key]+=1
    return summary
def main() -> int:
    retention={}
    try: results=run_gmail_inbox_runtime(alert_sender=build_alert_sender_from_environment(),retention_report=retention)
    except RuntimeError as exc: print(f"VOCANTA inbox runtime skipped: {exc}"); return 0
    summary=summarize_inbox_results(results); print("VOCANTA inbox runtime: "+", ".join(f"{value} {key}" for key,value in summary.items())); print(f"VOCANTA retention: {retention.get('archived_replies',0)} archived replies removed, {retention.get('audit_events',0)} audit events removed"); return 0
if __name__=="__main__": raise SystemExit(main())
