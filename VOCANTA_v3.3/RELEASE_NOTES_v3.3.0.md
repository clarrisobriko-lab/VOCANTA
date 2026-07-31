# VOCANTA 3.3, Employer Curated Greenhouse Discovery

VOCANTA 3.3 stops treating Greenhouse as one giant source.

## Production changes

- Greenhouse employer boards are controlled by a fail-closed registry.
- Only explicitly approved employers are queried.
- Canonical is disabled at source because its board is engineering dominated.
- Disabled employers generate no network request and no job records.
- Every approved employer has role-focus, international-hiring, sponsorship and automation metadata.
- Role-focus filtering occurs inside the employer connector before jobs enter the discovery engine.
- The dashboard reports configured, approved and blocked employer boards separately from job counts.
- `employer_boards.bat` displays the current production registry.
- Greenhouse job sources now identify the employer board, for example `Greenhouse:remotecom`.

## Launch policy

Greenhouse remains the only live ATS for the controlled application milestone. Adding an employer requires an intentional registry decision, not a code-level expansion of a generic Greenhouse source.
