from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.follow_up_store import complete_follow_up, due_follow_ups, generate_follow_up_queue, record_follow_up_failure
from intelligence.follow_up_messages import FollowUpMessage, generate_follow_up_message


class FollowUpSender(Protocol):
    def send(self, recipient: str, message: FollowUpMessage) -> str: ...


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    follow_up_id: int
    status: str
    reason: str
    delivery_id: str = ""


def process_follow_ups(connection, candidate_name: str, recipient_resolver, sender: FollowUpSender, *, now=None, limit: int=20, max_attempts: int=3, retry_minutes: int=60) -> list[DeliveryResult]:
    generate_follow_up_queue(connection,now=now); results=[]
    for row in due_follow_ups(connection,now=now,limit=limit):
        follow_up_id=int(row['id'] if hasattr(row,'keys') else row[0]); action=str(row['action'] if hasattr(row,'keys') else row[2])
        company=str(row['company'] if hasattr(row,'keys') else row[-3]); title=str(row['title'] if hasattr(row,'keys') else row[-2]); job_url=str(row['url'] if hasattr(row,'keys') else row[-1])
        recipient=(recipient_resolver(company,job_url) or '').strip()
        if not recipient:
            results.append(DeliveryResult(follow_up_id,'NO_RECIPIENT','no verified employer recipient available')); continue
        message=generate_follow_up_message(company,title,candidate_name,action)
        try: delivery_id=sender.send(recipient,message)
        except Exception as exc:
            retry=record_follow_up_failure(connection,follow_up_id,str(exc),max_attempts=max_attempts,retry_minutes=retry_minutes,now=now)
            results.append(DeliveryResult(follow_up_id,'RETRYABLE' if retry else 'FAILED',str(exc))); continue
        complete_follow_up(connection,follow_up_id,delivery_id=delivery_id or '',now=now)
        results.append(DeliveryResult(follow_up_id,'SENT','follow-up delivered',delivery_id or ''))
    return results
