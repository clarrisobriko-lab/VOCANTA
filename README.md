# VOCANTA 3.3

VOCANTA is a controlled job qualification and application automation system.

## Core production rule

Greenhouse is an ATS platform, not one giant job source. VOCANTA queries only employer boards explicitly approved in `config\greenhouse_employers.json`.

The packaged registry blocks Canonical at source because its board is engineering dominated. Remote is the initial approved direct Greenhouse employer board. A blocked board is not requested, scored, stored or opened in Chrome.

## Install

1. Extract the complete `VOCANTA_v3.3` folder.
2. Run `install.bat`.
3. Run `start_vocanta.bat`.

## Employer board control

Run:

```text
employer_boards.bat
```

This shows configured, approved and blocked Greenhouse employers and the reason for each decision.

The registry fails closed. Invalid, duplicated or missing employer configuration stops discovery rather than silently scouting unknown boards.

## Application policy

VOCANTA selects at most one eligible Greenhouse application per run. It never records a successful submission without confirmation evidence. Restricted own-words questions remain manual.
