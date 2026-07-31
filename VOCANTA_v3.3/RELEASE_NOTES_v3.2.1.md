# VOCANTA v3.2.1, 48 Hour Production Launch Hotfix

This release narrows the live pipeline to the only ATS currently supported end to end.

## Production controls

* Greenhouse is the sole active discovery connector.
* Aggregators and unsupported ATS connectors are not instantiated and make no network requests.
* Jobs with terminal automation or application history are suppressed before scoring, persistence, dashboard rendering, queue auditing, or browser launch.
* Temporary failures remain retryable.
* Empty queue output reports only that no new direct Greenhouse candidate is ready.

No browser bypass, CAPTCHA handling, or anti-bot circumvention is attempted.
