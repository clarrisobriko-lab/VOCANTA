# VOCANTA 3.4.0 Release Validation Evidence

## Release commit

`b3649ff504951b4cacd33bbc3129871d74159c58`

## CI evidence

Workflow: VOCANTA Tests

Run ID: `33851514114`

Event: scheduled validation on `main`

Result: success

Regression result: `476 passed, 13 subtests passed in 3.92s`

Python: CPython 3.13.15

## Gate status

The exact release commit has passed the automated regression gate required by `PRODUCTION_CRITICAL_PATH.md`.

The controlled live gate remains closed until a specific target job and approved applicant package are deliberately selected. No real employer submission is authorised by this validation record.

## Next controlled step

Run the documented dry run against one explicitly selected, policy compliant job using a recognised ATS adapter. The dry run must validate fields, documents, adapter routing and package identity without submitting. Any unsupported challenge, missing field or policy failure must stop execution.
