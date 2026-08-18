# Controlled Live Validation Gate

Production-critical implementation is merged. Live operation is gated by this checklist.

## Preconditions
- CI for the exact release commit is green.
- Candidate profile and application documents are explicitly approved.
- Target job is explicitly selected and within configured country/role policy.
- ATS adapter is recognized; generic/unknown ATS remains fail-closed.
- No unresolved ambiguous submission exists for the target application.

## Dry run
1. Resolve the target job and ATS adapter.
2. Build the application package from approved evidence only.
3. Validate required fields and document paths without submitting.
4. Record adapter, target URL, package identity, and validation result.
5. Any missing field, unsupported challenge, or policy failure stops execution.

## Controlled live run
1. Require explicit live-submit authorization for the selected target.
2. Execute exactly one submission attempt.
3. Treat timeout/navigation ambiguity as UNKNOWN, never as safe-to-retry.
4. Mark SUBMITTED only when recognized confirmation evidence is present.
5. Persist outcome/evidence and trigger downstream tracking once.

## Release acceptance
The controlled live milestone passes only when a selected application produces recognized confirmation evidence, persisted tracking state, and no duplicate submission. CAPTCHA/MFA/manual-intervention states are not bypassed and remain fail-closed.
