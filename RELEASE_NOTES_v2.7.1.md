# VOCANTA v2.7.1

## Cloudflare removal policy

VOCANTA no longer uses Himalayas as a connector and will not open Himalayas pages.
Known Cloudflare-protected domains are blocked before browser launch. If another
source redirects to a blocked domain, VOCANTA closes the automated route
immediately and continues to the next job.

This release does not attempt to bypass Cloudflare or any anti-bot security. It
removes those sources from the automated workflow entirely.
