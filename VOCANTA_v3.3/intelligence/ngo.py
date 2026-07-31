from dataclasses import dataclass

from core.models import Job


NGO_ORGANISATIONS = {
    "unicef": 30,
    "unhcr": 30,
    "international organization for migration": 30,
    "iom": 25,
    "save the children": 25,
    "oxfam": 25,
    "amnesty international": 25,
    "red cross": 22,
    "norwegian refugee council": 22,
    "danish refugee council": 22,
    "international rescue committee": 22,
    "médecins sans frontières": 22,
    "medecins sans frontieres": 22,
    "l'arche": 18,
}

NGO_SIGNALS = {
    "nonprofit": 12,
    "non-profit": 12,
    "charity": 12,
    "human rights": 15,
    "humanitarian": 15,
    "refugee": 15,
    "legal aid": 12,
    "international development": 12,
    "foundation": 8,
    "advocacy": 10,
    "community development": 10,
}


@dataclass(frozen=True, slots=True)
class NgoAssessment:
    is_ngo: bool
    score: int
    label: str


def assess_ngo(job: Job) -> NgoAssessment:
    text = " ".join(
        (job.company, job.title, job.description, job.employment_type)
    ).lower()

    organisation_score = max(
        (score for phrase, score in NGO_ORGANISATIONS.items() if phrase in text),
        default=0,
    )
    signal_score = min(
        30,
        sum(score for phrase, score in NGO_SIGNALS.items() if phrase in text),
    )
    score = min(40, organisation_score + signal_score)

    if score >= 25:
        label = "NGO_PRIORITY"
    elif score > 0:
        label = "NGO_POSSIBLE"
    else:
        label = "CORPORATE"

    return NgoAssessment(score > 0, score, label)
