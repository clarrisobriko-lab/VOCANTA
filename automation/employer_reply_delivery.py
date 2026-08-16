from __future__ import annotations

from core.employer_reply_store import mark_reply_send_failed, mark_reply_sent


def send_approved_reply(connection,message_id: str,recipient: str | None,sender) -> bool:
    row=connection.execute("SELECT d.subject,d.body,d.status,r.sender,r.thread_id,r.internet_message_id,r.references_header FROM employer_reply_drafts d JOIN employer_responses r ON r.message_id=d.message_id WHERE d.message_id=?",(message_id,)).fetchone()
    if row is None or str(row[2])!='APPROVED': return False
    target=(recipient or str(row[3])).strip()
    if not target: return False
    try:
        sender.send(target,str(row[0]),str(row[1]),thread_id=str(row[4]),in_reply_to=str(row[5]),references=str(row[6]))
    except TypeError:
        try: sender.send(target,str(row[0]),str(row[1]))
        except Exception as exc: mark_reply_send_failed(connection,message_id,str(exc)); return False
    except Exception as exc:
        mark_reply_send_failed(connection,message_id,str(exc)); return False
    mark_reply_sent(connection,message_id); return True
