from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FollowUpMessage:
    subject: str
    body: str


def generate_follow_up_message(company: str, title: str, candidate_name: str, action: str) -> FollowUpMessage:
    company = (company or "the company").strip()
    title = (title or "the position").strip()
    candidate_name = (candidate_name or "Candidate").strip()
    second = action == "SECOND_FOLLOW_UP"
    subject = f"Follow-up on application for {title}"
    opening = (
        f"I am following up once more regarding my application for the {title} position at {company}."
        if second else
        f"I am writing to follow up on my application for the {title} position at {company}."
    )
    body = (
        f"Dear Hiring Team,\n\n{opening} I remain very interested in the opportunity and would appreciate any update you may be able to share regarding the status of my application.\n\n"
        "Thank you for your time and consideration. I would be pleased to provide any further information required.\n\n"
        f"Kind regards,\n{candidate_name}"
    )
    return FollowUpMessage(subject, body)
