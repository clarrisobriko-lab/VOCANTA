from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerifiedClaim:
    key: str
    evidence: tuple[str, ...]


# Every claim used for vacancy matching must point to verified applicant evidence.
# Evidence may come from documented work history or an explicit applicant confirmation.
# Vacancy text may select or rank these claims, but may never create a new claim.
CLAIMS: tuple[VerifiedClaim, ...] = (
    VerifiedClaim("recruitment", ("Human Resource Manager: recruitment and employee management", "HR Personnel: recruitment support")),
    VerifiedClaim("onboarding", ("Human Resource Manager: onboarding", "Jam Oil and Gas: onboarding and training programmes")),
    VerifiedClaim("employee relations", ("Human Resource Manager: employee relations",)),
    VerifiedClaim("human resources", ("Human Resource Manager", "HR Personnel")),
    VerifiedClaim("records management", ("Human Resource Manager: personnel records", "HR Personnel: employee record management")),
    VerifiedClaim("reporting", ("Human Resource Manager: administrative reports", "Jam Oil and Gas: management reporting")),
    VerifiedClaim("scheduling", ("Jam Oil and Gas: staff scheduling", "LEDAP: case schedules", "HR Personnel: calendars and meetings")),
    VerifiedClaim("compliance", ("Human Resource Manager: policy implementation and compliance",)),
    VerifiedClaim("legal research", ("Legal Associate: legal research",)),
    VerifiedClaim("contract management", ("Legal Associate: drafted contracts",)),
    VerifiedClaim("policy", ("Human Resource Manager: developed and implemented policies",)),
    VerifiedClaim("client communication", ("LEDAP: client communication and consultations",)),
    VerifiedClaim("documentation", ("LEDAP: legal documents, briefs and case files", "Legal Associate: case documentation")),
    VerifiedClaim("calendar management", ("HR Personnel: managed calendars and meetings",)),
    VerifiedClaim("executive support", ("HR Personnel: executive correspondence", "Human Resource Manager: reports to leadership")),
    VerifiedClaim("stakeholder management", ("LEDAP: worked with NGOs and government agencies on human rights initiatives",)),
    VerifiedClaim("administrative support", ("HR Personnel: managed calendars, meetings and executive correspondence",)),
    VerifiedClaim("training", ("Jam Oil and Gas: training programmes",)),
    VerifiedClaim("zoom", ("Applicant confirmed years of Zoom use",)),
    VerifiedClaim("slack", ("Applicant confirmed current Slack use",)),
)


def verified_claims() -> dict[str, VerifiedClaim]:
    return {claim.key: claim for claim in CLAIMS}


def verified_skill_keys() -> set[str]:
    return set(verified_claims())


def evidence_for(skill: str) -> tuple[str, ...]:
    claim = verified_claims().get(skill)
    return claim.evidence if claim else ()
