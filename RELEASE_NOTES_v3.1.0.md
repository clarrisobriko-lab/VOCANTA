# VOCANTA 3.1.0

VOCANTA 3.1 shifts the production milestone from job discovery to verified application completion.

## Application execution

- Added a semantic question engine for country, nationality, education, sponsorship, relocation, travel, employer count, privacy acknowledgements and other structured answers.
- Added native select, dynamic combobox, radio and checkbox handling.
- Added multi-step form continuation with rescanning after each page transition.
- Added AI-restriction detection. Questions requiring the applicant's own words are never generated or auto-filled.
- Preserved the rule that FOLLOW_UP is only reached after recognised submission evidence.

## Applicant profile

- Added structured education and employment history.
- Added nationality, region, current location, relocation, remote and country preferences.
- Demographic data remains optional and disabled by default.
- Existing profiles are migrated automatically without losing prior information.

## Diagnostics

- Every browser run writes a JSON application report under the persistent data/automation_reports directory.
- Reports identify detected fields, automatic fills, manual requirements, document uploads, submission state and evidence.
