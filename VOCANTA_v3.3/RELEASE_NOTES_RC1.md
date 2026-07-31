# VOCANTA RC1

RC1 is the controlled 48-hour launch candidate.

## Launch scope

- Direct Greenhouse discovery only
- One highest-ranked eligible application per run
- Discovery completes before Chrome opens
- Unsupported marketplaces and ATS platforms are never instantiated
- Verified submission evidence remains mandatory
- Safe retry utility for the latest unconfirmed Greenhouse run
- Confirmed or applied jobs can never be reopened by the retry utility

## Acceptance command

Run `start_vocanta.bat`.

When a previous unconfirmed test run is blocking the only suitable role, run
`retry_last_unconfirmed.bat` once, then run `start_vocanta.bat` again.
