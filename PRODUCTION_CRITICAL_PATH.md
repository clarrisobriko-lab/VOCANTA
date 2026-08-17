# Production-critical release gate

VOCANTA may be described as production-ready only when all of these invariants hold:

- Supported ATS routing is explicit: Greenhouse, Lever, Ashby, SmartRecruiters, and Workday.
- Unknown ATS hosts fail closed and cannot auto-submit.
- Final submission is armed only after required fields and approved documents are present.
- Human/security verification and account verification stop autonomous execution.
- AI-restricted employer questions require the applicant's own response.
- A submit click without recognised confirmation becomes `UNKNOWN` and is never automatically retried.
- `SUBMITTED`/success is emitted only from recognised confirmation evidence.
- Application diagnostics preserve detected fields, uploads, state, evidence, and screenshot/report references.
- Recovery has a bounded retry budget and does not retry ambiguous submissions.
- Regression CI must pass for the exact release commit before merge to `main`.

The controlled live-application gate remains intentionally human-authorised. CI and fixtures validate automation mechanics; they do not constitute permission to submit a real application to an employer.