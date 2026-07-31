# VOCANTA v2.9.2

- Fixed the startup stall after the final connector completes.
- Replaced the slow per-company employer-memory loop with one set-based database operation.
- Added batch persistence for job intelligence.
- Added visible phase logs after discovery so startup progress is never silent.
- Startup now continues if non-critical employer analytics fail.
- Corrected installer version text.
