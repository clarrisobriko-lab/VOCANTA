from config.settings import EXCLUDED_TITLE_TERMS, GENERIC_TITLES, TARGET_ROLE_WEIGHTS
from core.models import Job


class Matcher:
    def is_relevant(self, job: Job) -> bool:
        title = " ".join(job.title.strip().lower().split())
        if not title or title in GENERIC_TITLES:
            return False
        if any(term in title for term in EXCLUDED_TITLE_TERMS):
            return False
        return any(term in title for term in TARGET_ROLE_WEIGHTS)
