from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressSignal:
    status: str
    confidence: int
    reason: str


def classify_progress(subject: str, body: str) -> ProgressSignal:
    text=f"{subject} {body}".lower()
    if any(term in text for term in ("offer of employment","job offer","pleased to offer you","offer letter")):
        return ProgressSignal("OFFER",95,"offer language detected")
    if any(term in text for term in ("invite you to interview","interview invitation","schedule an interview","interview availability","interview with")):
        return ProgressSignal("INTERVIEW",90,"interview language detected")
    if any(term in text for term in ("unfortunately","not moving forward","will not be progressing","other candidates","not selected")):
        return ProgressSignal("REJECTED",85,"rejection language detected")
    if any(term in text for term in ("application received","thank you for applying","received your application")):
        return ProgressSignal("APPLIED",85,"application acknowledgement detected")
    return ProgressSignal("UNKNOWN",0,"no reliable application-progress signal")
