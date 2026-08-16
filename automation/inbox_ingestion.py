from __future__ import annotations

from dataclasses import dataclass

from core.employer_response_store import record_employer_response
from intelligence.application_matcher import match_application
from intelligence.employer_responses import classify_employer_response


@dataclass(frozen=True, slots=True)
class InboxResult:
    message_id: str
    status: str
    job_id: int | None = None


def process_inbox_messages(connection, messages) -> list[InboxResult]:
    results=[]
    for message in messages:
        message_id=str(message.get("id","")).strip()
        sender=str(message.get("sender",message.get("from",""))).strip()
        subject=str(message.get("subject","")).strip()
        body=str(message.get("body",message.get("snippet",""))).strip()
        received_at=str(message.get("received_at",message.get("date",""))).strip()
        if not message_id:
            results.append(InboxResult("","INVALID")); continue
        job_id=match_application(connection,sender,subject,body)
        if job_id is None:
            results.append(InboxResult(message_id,"UNMATCHED")); continue
        classification=classify_employer_response(subject,body)
        created=record_employer_response(connection,job_id,message_id,sender,subject,classification,received_at=received_at)
        results.append(InboxResult(message_id,"PROCESSED" if created else "DUPLICATE",job_id))
    return results
