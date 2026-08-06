# VOCANTA v2.9.6

- Fixed automation crash caused by missing `job_intelligence.primary_reason`.
- Added idempotent schema migration before automation queries run.
- Migration discovery now scans all VOCANTA databases in Downloads and Desktop.
- Databases are integrity checked and schema validated.
- Selection uses the highest numeric VOCANTA version, then modified time as a tie breaker.
- Startup logs show the selected version and exact selection reason.
