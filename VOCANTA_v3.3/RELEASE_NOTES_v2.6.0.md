# VOCANTA v2.6.0 Release Notes

## Release objective

Version 2.6.0 implements the highest priority safety and reliability work from
the post 1.6 roadmap. It focuses on eligibility correctness, submission
control, durable recovery, duplicate prevention, packaging, and test coverage.

## Implemented

### Unified eligibility policy

1. Added one versioned policy engine used by filtering, scoring, intelligence,
   opportunity selection, and application automation.
2. Added explicit `BLOCK`, `REVIEW`, `APPLY`, and `PRIORITY` decisions.
3. Added structured reason codes, matched evidence, confidence, and rule
   version persistence.
4. Added boundary aware and negation aware text matching.
5. Added hard blocks for restricted geography, required local languages,
   unsupported markets, local residence requirements, and unavailable
   sponsorship where relocation would be required.
6. Preserved worldwide remote roles where employer sponsorship is irrelevant.

### Safe application execution

1. Removed `Apply`, `Apply now`, and generic `Submit` from the default final
   submission controls.
2. Final controls now require exact normalized text.
3. Added explicit applicant tracking system adapters.
4. Greenhouse and Lever are the only adapters permitted to submit
   automatically in this release.
5. Ashby, SmartRecruiters, Workday, and generic forms stop for human review.
6. An unconfirmed final click is recorded as `UNKNOWN` and is never retried
   automatically.

### Durable state and idempotency

1. Added the `application_runs` table with a unique idempotency key.
2. Added validated state transitions from creation through confirmation.
3. Persisted state before browser preparation, before the final click, after
   the click, and after confirmation.
4. Persisted confirmation phrase, confirmation URL, screenshot path, and last
   error.
5. Only `CONFIRMED` marks the job as applied.
6. Added canonical URL normalization for discovery and database upserts.
7. Added profile and document hashes to each application identity.

### Packaging and privacy

1. Updated the application version and HTTP user agent to 2.6.
2. Added `python-docx` to the declared dependencies.
3. Added `test.bat` and made installation run the complete suite.
4. Converted the remaining nonstandard history tests to `unittest`.
5. Removed personal contact details from source defaults and example profile
   data.
6. Added migration from schema 2.5 to schema 2.6.

## Verification completed

1. Python compilation completed without errors.
2. The standard command ran 41 tests with 41 passing.
3. Regression cases verified that `EU only`, `UK only`, and `US only` are
   blocked and score zero.
4. Negated geography text was verified not to false block.
5. Negative sponsorship text was verified not to trigger a positive
   sponsorship rule.
6. Regional `work from anywhere` language was verified not to bypass a regional
   restriction.
7. Exact final control matching was verified against `Apply now` and `Submit
   application`.
8. Adapter allowlists were verified for Greenhouse, Lever, Workday, and generic
   forms.
9. Canonical URL deduplication and application run idempotency were verified.
10. Invalid state transitions and ambiguous submission terminal handling were
    verified.
11. A representative version 2.5 database schema was migrated successfully to
    version 2.6.

## Deliberately deferred

1. Live browser submission tests were not run against real employer forms
   because they could create real applications. A controlled staging fixture is
   recommended before enabling additional automatic submission adapters.
2. Tailored document content still needs the roadmap redesign that derives all
   claims from the master CV instead of fixed templates.
3. Connector expansion and connector contract testing remain later release
   work.
4. Historical canonical duplicates are not merged automatically. Version 2.6
   prevents new duplicates without destructively rewriting existing records.
