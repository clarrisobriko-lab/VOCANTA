# VOCANTA v2.9.7

Production queue consistency release.

- Dashboard APPLY and PRIORITY counts now use the exact automation queue rules.
- Jobs with previous application runs or terminal automation outcomes display as NOT_QUEUED.
- Every queue entry receives a unique queue ID and a persistent audit record.
- Discovery, queue entry and pre-browser filters log ACCEPTED or REJECTED with the exact reason.
- Empty-queue diagnostics list each affected company, role, score and rejection reason.
- Live automation starts only when a genuinely queueable job exists.
- The stream worker and automated application runner now use the same queue criteria.
