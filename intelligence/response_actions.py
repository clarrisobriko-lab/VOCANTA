from __future__ import annotations

from dataclasses import dataclass

from intelligence.employer_responses import EmployerResponse


@dataclass(frozen=True, slots=True)
class ResponseAction:
    priority: str
    action: str


def action_for_response(response: EmployerResponse) -> ResponseAction:
    if response.status=="OFFER": return ResponseAction("URGENT","Review offer and prepare response")
    if response.status=="INTERVIEW": return ResponseAction("HIGH","Review interview request and prepare availability")
    if response.status=="ACTION_REQUIRED": return ResponseAction("HIGH","Review employer request and provide required information")
    if response.status=="REJECTED": return ResponseAction("LOW","Record outcome and close active follow ups")
    return ResponseAction("MEDIUM","Review employer message manually")
