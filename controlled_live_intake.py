from __future__ import annotations

from urllib.request import Request, urlopen

from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, authorize_target
from core.database import Database
from core.models import Job


def verify_target_is_live(url: str) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 VOCANTA controlled-live-intake"})
    with urlopen(request, timeout=15) as response:
        status = getattr(response, "status", 200)
        final_url = response.geturl()
        if status >= 400:
            raise RuntimeError(f"Controlled target intake blocked: target returned HTTP {status}")
        authorize_target(final_url)


def main() -> int:
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    authorize_target(target.application_url)
    verify_target_is_live(target.application_url)

    job = Job(
        company=target.employer,
        title=target.title,
        location="Remote, international",
        source="ControlledLiveIntake",
        url=target.application_url,
        description=(
            "Authorized controlled live validation target. Administrative Assistant role. "
            "This intake exists only to exercise VOCANTA's non submitting dry run and must "
            "not be substituted for another vacancy."
        ),
        score=100,
    )

    database = Database()
    try:
        database.upsert_jobs([job])
        row = database.connection.execute(
            "SELECT id, company, title, url FROM jobs WHERE canonical_url = ? LIMIT 1",
            (target.application_url.rstrip("/"),),
        ).fetchone()
        if row is None:
            raise RuntimeError("Controlled target intake failed: target was not persisted")
        print("CONTROLLED LIVE INTAKE: READY")
        print(f"Job ID: {row['id']}")
        print(f"Target: {row['company']} | {row['title']}")
        print("Submission: DISABLED. No application browser was launched.")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
