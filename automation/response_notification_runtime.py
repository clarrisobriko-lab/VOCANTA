from __future__ import annotations

from automation.response_notifications import build_response_notification
from core.response_notification_store import claim_notification, mark_notification_delivered
from intelligence.employer_responses import EmployerResponse


def notify_processed_responses(connection, results, sender) -> list[str]:
    delivered=[]
    for result in results:
        if result.status!='PROCESSED' or result.job_id is None: continue
        row=connection.execute("SELECT er.classification,er.confidence,er.reason,er.sender,j.company,j.title FROM employer_responses er JOIN jobs j ON j.id=er.job_id WHERE er.message_id=?",(result.message_id,)).fetchone()
        if row is None: continue
        response=EmployerResponse(str(row[0]),int(row[1]),str(row[2]))
        note=build_response_notification(result.message_id,str(row[4]),str(row[5]),str(row[3]),response)
        if note is None: continue
        if not claim_notification(connection,note.message_id,note.priority): continue
        try: sender.send(note.subject,note.body)
        except Exception:
            continue
        mark_notification_delivered(connection,note.message_id); delivered.append(note.message_id)
    return delivered
