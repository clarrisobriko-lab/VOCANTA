# VOCANTA v2.9.4

Production source and queue cleanup.

- RemoteOK is fully disabled, not merely discovery-only.
- Jobgether is removed from Lever discovery and blocked from browser automation.
- Himalayas, RemoteOK and Jobgether domains are hard-blocked before any browser opens.
- Unsupported office locations, including China, remain rejected.
- Stale human-action queue entries for rejected jobs are automatically closed.
- Connector HTTP timeout is reduced to prevent prolonged startup stalls.
- Gmail human-action notifications remain enabled.
