# VOCANTA v2.9.0 Production Notification Release

## Critical fixes

- Gmail configuration now persists in `%LOCALAPPDATA%\VOCANTA` across upgrades.
- Existing v2.8.1 email settings are migrated automatically from the old release folder.
- OAuth client configuration and notification outbox now use persistent storage.
- Every application requiring human action triggers an email, not only high-value applications.
- Notification delivery retries three times before creating an `.eml` fallback.
- Logs now state the exact settings path, credential service, delivery attempt and failure reason.
- Human-action emails contain the direct job link, reason, assessment and available tailored documents.

## Upgrade

Extract this ZIP into a new folder and run `install.bat`, then `start_vocanta.bat`.
Your applicant profile, documents and Gmail credentials remain in the persistent VOCANTA data directory.
