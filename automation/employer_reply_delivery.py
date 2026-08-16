from __future__ import annotations

from core.employer_reply_store import mark_reply_send_failed, mark_reply_sent


def send_approved_reply(connection,message_id: str,recipient: str,sender) -> bool:
    row=connection.execute("SELECT subject,body,status FROM employer_reply_drafts WHERE message_id=?",(message_id,)).fetchone()
    if row is None or str(row[2])!='APPROVED': return False
    recipient=recipient.strip()
    if not recipient: return False
    try: sender.send(recipient,str(row[0]),str(row[1]))
    except Exception as exc:
        mark_reply_send_failed(connection,message_id,str(exc)); return False
    mark_reply_sent(connection,message_id); return True
