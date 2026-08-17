from __future__ import annotations

from core.employer_reply_store import claim_reply_send, ensure_reply_schema, mark_reply_send_failed, mark_reply_sent, record_reply_event


def _thread_context(connection,message_id: str):
    try: return connection.execute("SELECT sender,thread_id,internet_message_id,references_header FROM employer_responses WHERE message_id=?",(message_id,)).fetchone()
    except Exception: return None


def send_approved_reply(connection,message_id: str,recipient: str | None,sender) -> bool:
    ensure_reply_schema(connection)
    row=connection.execute("SELECT subject,body,status FROM employer_reply_drafts WHERE message_id=?",(message_id,)).fetchone()
    if row is None or str(row[2])!='APPROVED': return False
    if not claim_reply_send(connection,message_id): return False
    context=_thread_context(connection,message_id); stored_recipient=str(context[0]) if context is not None else ''; target=(recipient or stored_recipient).strip()
    if not target:
        mark_reply_send_failed(connection,message_id,'Missing recipient'); return False
    record_reply_event(connection,message_id,'SEND_ATTEMPT',target)
    try:
        if context is not None: gmail_message_id=sender.send(target,str(row[0]),str(row[1]),thread_id=str(context[1]),in_reply_to=str(context[2]),references=str(context[3]))
        else: gmail_message_id=sender.send(target,str(row[0]),str(row[1]))
    except TypeError:
        try: gmail_message_id=sender.send(target,str(row[0]),str(row[1]))
        except Exception as exc: mark_reply_send_failed(connection,message_id,str(exc)); return False
    except Exception as exc:
        mark_reply_send_failed(connection,message_id,str(exc)); return False
    mark_reply_sent(connection,message_id,str(gmail_message_id or '')); return True
