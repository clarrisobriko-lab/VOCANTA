from core.models import Job
from automation.idempotency import canonicalize_job_url
from intelligence.eligibility import is_production_eligible


class JobFilter:
    def has_supported_location(self, job: Job) -> bool:
        return is_production_eligible(job)

    def has_unique_url(self, job: Job, seen_urls: set[str]) -> bool:
        url = canonicalize_job_url(job.url)
        if not url or url in seen_urls:
            return False
        seen_urls.add(url)
        return True
