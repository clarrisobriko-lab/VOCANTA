# VOCANTA v2.6.1 Release Notes

## Objective

Version 2.6.1 repairs the two operational failures observed after v2.6.0:
Gmail authentication rejection and loss of the active employer application
page during human review.

## Gmail OAuth

1. Added desktop Google OAuth connection with one time browser consent.
2. Added automatic access token refresh.
3. Added Gmail API message delivery using the `gmail.send` scope.
4. Stored renewable authorization in Windows Credential Manager.
5. Retained App Password mode as an explicit legacy fallback.
6. Added whitespace normalization for formatted App Passwords.
7. Added automatic resend of saved EML drafts after OAuth setup succeeds.

## Notification reliability

1. Added durable notification delivery records.
2. Added unique event deduplication keys.
3. Added `QUEUED`, `SENDING`, `SENT`, `AUTH_REQUIRED`, `OUTBOX` and `FAILED`
   states.
4. Prevented a sent notification from returning to a retryable state.
5. Preserved an EML draft whenever authorization or delivery fails.

## Browser recovery

1. Added a page registry for the full Playwright browser context.
2. Added popup and new tab detection after Apply, Continue and Submit actions.
3. Added rebinding when the original employer page closes.
4. Added form and ATS signals when selecting the active page.
5. Persisted the active employer URL with each application run.

## Safety invariants retained

1. Only Greenhouse and Lever may submit automatically.
2. Final controls require exact approved text.
3. Every final click requires persisted `SUBMITTING` state first.
4. `SUBMITTED` and `UNKNOWN` runs cannot retry automatically.
5. Only a confirmed submission marks the job as applied.

## Setup boundary

Google requires the user to create or supply a Desktop OAuth client and approve
the initial consent screen. This security decision cannot be automated. After
that one time step, VOCANTA refreshes authorization and sends notifications
without asking for another password.
