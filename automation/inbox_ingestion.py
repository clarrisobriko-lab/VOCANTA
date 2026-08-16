from __future__ import annotations

from dataclasses import dataclass

from core.employer_reply_store import save_reply_draft
from core.employer_response_store import record_employer_response
from intelligence.application_matcher import match_application
from intelligence.employer_reply_drafts import build_reply_draft
from intelligence.employer_responses import classify_employer_response


@dataclass(frozen=True, slots=True)
class InboxResult:
    message_id: str
    status: str
    job_id: int | None=None


def process_inbox_messages(connection,messages,*,candidate_name: str="Candidate") -> list[InboxResult]:
    results=[]
    for message in messages:
        message_id=str(message.get('id','')).strip(); sender=str(message.get('sender',message.get('from',''))).strip(); subject=str(message.get('subject','')).strip(); body=str(message.get('body',message.get('snippet',''))).strip(); received_at=str(message.get('received_at',message.get('date',''))).strip()
        if not message_id: results.append(InboxResult('','INVALID')); continue
        job_id=match_application(connection,sender,subject,body)
        if job_id is None: results.append(InboxResult(message_id,'UNMATCHED')); continue
        classification=classify_employer_response(subject,body)
        created=record_employer_response(connection,job_id,message_id,sender,subject,classification,received_at=received_at,thread_id=str(message.get('thread_id','')),internet_message_id=str(message.get('internet_message_id','')),references_header=str(message.get('references','')))
        if created:
            row=connection.execute('SELECT company,title FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is not None:
                draft=build_reply_draft(classification.status,str(row[0]),str(row[1]),candidate_name,subject)
                if draft is not None: save_reply_draft(connection,message_id,job_id,draft)
        results.append(InboxResult(message_id,'PROCESSED' if created else 'DUPLICATE',job_id))
    return results
