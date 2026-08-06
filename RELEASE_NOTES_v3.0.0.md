# VOCANTA 3.0.0

VOCANTA 3.0 is a production-hardening release built from the v2.9.9 codebase.

## Reliability

- Added a single deterministic discovery gate for validation, URL deduplication, eligibility, role relevance, scoring and intelligence assessment.
- Added explicit rejection classifications so irrelevant engineering roles, unsupported locations, malformed vacancies, duplicates and weak matches are measurable rather than silently discarded.
- Normalised all incoming job fields and clamped scores at the immutable model boundary.
- Added resilient HTTP sessions with bounded retries, backoff, connection pooling, `Retry-After` support and a version-correct user agent.
- Added typed failure handling when a connector endpoint returns non-JSON content.

## Engineering quality

- Added `pyproject.toml` as the canonical package, dependency and test configuration.
- Fixed test portability so the suite runs from the project root without manually setting `PYTHONPATH`.
- Updated application version metadata to 3.0.0.
- Added dedicated v3.0 discovery and model tests.

## Compatibility

- Existing database schema, migration path, applicant profile, email configuration, assets, exports, browser automation and Windows launch scripts are preserved.
- CAPTCHA, Cloudflare and employer security controls are not bypassed.

## Installer correction

- Added `requirements-test.txt` for verification-only dependencies.
- Made `test.bat` self-install `pytest` when absent.
- Updated `install.bat` so a clean Windows installation no longer fails with `No module named pytest`.
