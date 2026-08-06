# VOCANTA v2.8.1

## Greenhouse autofill production fix

Root cause: the previous detector searched the complete HTML for words such as `recaptcha`. Greenhouse loads CAPTCHA libraries in ordinary application pages, so a hidden script caused a false human-verification classification before autofill began.

Changes:

- Verification now requires a visible CAPTCHA iframe or container, a dedicated challenge URL, or visible challenge text without a normal application form.
- Standard Greenhouse forms are not blocked merely because CAPTCHA scripts exist in page source.
- Every verification decision is written to the VOCANTA log with the URL, whether a standard form was visible, and the exact detection reasons.
- Terminal messages now display the exact reason whenever human action is genuinely required.
- Existing Greenhouse autofill remains enabled and begins immediately when the form is visible.
