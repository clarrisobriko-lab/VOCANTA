from __future__ import annotations

from dataclasses import dataclass

from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response


@dataclass(frozen=True, slots=True)
class ResponseNotification:
    message_id: str
    priority: str
    subject: str
    body: str


def build_response_notification(message_id: str, company: str, title: str, sender: str, response: EmployerResponse) -> ResponseNotification | None:
    action=action_for_response(response)
    if action.priority not in {"URGENT","HIGH"}: return None
    subject=f"VOCANTA {action.priority}: {company} {response.status}"
    body=f"{company}\n{title}\n{response.status}\n{action.action}\nFrom: {sender}"
    return ResponseNotification(message_id,action.priority,subject,body)


def deliver_response_notifications(notifications, sender) -> list[str]:
    delivered=[]
    for notification in notifications:
        sender.send(notification.subject,notification.body)
        delivered.append(notification.message_id)
    return delivered
