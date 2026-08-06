# VOCANTA v2.9.1

Production repair release.

- Sends human-action email immediately when an application pauses.
- Recovers Gmail OAuth settings from persistent and previous VOCANTA locations.
- Repairs legacy Credential Manager service and email-case mismatches automatically.
- Retries unsent notification records instead of suppressing them permanently.
- Retries saved email outbox drafts at the start of an automation run.
- Blocks RemoteOK and Jobgether marketplace pages from browser automation.
- Expands verified Greenhouse and Lever submit detection.
- Logs every visible action control and the exact acceptance or rejection reason.
- Restarts the browser once after a pre-submission TargetClosedError.
- Version updated to 2.9.1.

Validation: 78 automated tests passed.
