# VOCANTA 3.4.0

VOCANTA 3.4 closes the production-critical automation contract.

## Production ATS coverage

- Greenhouse, Lever, Ashby, SmartRecruiters, and Workday are explicit supported adapters.
- Unknown ATS platforms remain fail-closed and cannot auto-submit.
- Contract regression tests enforce adapter routing, confirmation evidence, unique host ownership, and generic fail-closed behaviour.

## Submission safety

- Human/security and account-verification gates stop autonomous execution.
- AI-restricted questions remain human-only.
- Ambiguous post-submit outcomes remain `UNKNOWN` and are not automatically retried.
- Success requires recognised submission confirmation evidence.

## Release policy

Production readiness requires green regression CI for the exact release commit. A real employer submission remains a separately authorised controlled-live action.