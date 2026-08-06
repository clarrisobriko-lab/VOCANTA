# VOCANTA v2.9.9

Production status-repair release.

- Repairs incorrect FOLLOW_UP states that have no confirmed submission evidence.
- Treats form filling, human verification, manual review, notifications and failed runs as incomplete applications, not submitted applications.
- Preserves FOLLOW_UP only when a submission is recorded as SUBMITTED or CONFIRMED.
- Resets repaired jobs to NEW and clears false applied and follow-up dates.
- Adds a permanent job status audit table with job ID, previous status, new status, stage, reason and timestamp.
- Runs status repair immediately after database migration and again at startup before revalidation and queue creation.
- Ensures repaired eligible jobs can move from NEW to APPLY and enter the automation queue.
