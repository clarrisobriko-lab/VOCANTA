# VOCANTA v2.9.5

- Enforces hard location and visa eligibility before jobs enter the database or automation queue.
- Allows explicit worldwide remote roles.
- Allows target-country roles only when sponsorship, relocation, or international applications are explicit.
- Blocks regional-only and unclear remote locations.
- Purges migrated ineligible jobs that have no genuine application history.
- Starts the live automation worker immediately after the first eligible job is persisted, while remaining connectors continue discovery.
