# VOCANTA v2.9.9

Production status integrity release.

- Repairs every false `FOLLOW_UP` state that lacks durable submission evidence.
- Legacy application-history rows can no longer preserve an invalid `FOLLOW_UP` state.
- Queue count, diagnostics, decision and candidate selection run a final status repair before evaluating jobs.
- Automated application startup performs and displays a final repair audit.
- `FOLLOW_UP` cannot be assigned to a new job unless a confirmed submission exists or the job is already `APPLIED`.
- Adds regression tests for stale history, transition guarding and pre-queue repair.
