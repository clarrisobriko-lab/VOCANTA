from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReplyDraft:
    subject: str
    body: str
    requires_approval: bool = True


def build_reply_draft(classification: str, company: str, title: str, candidate_name: str, original_subject: str = "") -> ReplyDraft | None:
    subject=original_subject.strip()
    if subject and not subject.lower().startswith("re:"): subject=f"Re: {subject}"
    if not subject: subject=f"Re: {company} {title}"
    name=candidate_name.strip() or "Candidate"
    if classification=="INTERVIEW":
        body=f"Thank you for reaching out regarding the {title} position at {company}. I am pleased to continue the conversation. Please send the available interview times and I will confirm promptly.\n\nKind regards,\n{name}"
    elif classification=="OFFER":
        body=f"Thank you for the offer for the {title} position at {company}. I appreciate the opportunity and would like to review the terms carefully before responding. Please let me know the response deadline and any documents I should consider.\n\nKind regards,\n{name}"
    elif classification=="ACTION_REQUIRED":
        body=f"Thank you for your message regarding the {title} position at {company}. I have received your request and will provide the requested information promptly.\n\nKind regards,\n{name}"
    else:
        return None
    return ReplyDraft(subject,body,True)
