from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmployerResponse:
    status: str
    confidence: int
    reason: str


def classify_employer_response(subject: str, body: str) -> EmployerResponse:
    text=f"{subject}\n{body}".lower()
    offer=("offer letter","pleased to offer","offer of employment","employment offer")
    interview=("interview","schedule a call","schedule a conversation","availability for a call","meet with the team")
    rejection=("not moving forward","will not be moving forward","other candidates","another candidate","unfortunately","not selected")
    information=("additional information","more information","please provide","could you provide","send us","complete the assessment")
    if any(term in text for term in offer): return EmployerResponse("OFFER",95,"offer language detected")
    if any(term in text for term in interview): return EmployerResponse("INTERVIEW",90,"interview or scheduling language detected")
    if any(term in text for term in rejection): return EmployerResponse("REJECTED",88,"rejection language detected")
    if any(term in text for term in information): return EmployerResponse("ACTION_REQUIRED",80,"employer requested further information or action")
    return EmployerResponse("REVIEW",40,"response requires human review")
