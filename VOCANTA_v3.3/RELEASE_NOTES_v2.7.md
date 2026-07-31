# VOCANTA v2.7

## Live Application Guardrails

This release is focused on going live with suitable applications, not adding cosmetic features.

* Rejects United States-only, Canada-only, regional-only and local-residency roles before browser launch.
* Requires explicit worldwide eligibility, international hiring, sponsorship or relocation evidence for automatic application.
* Blocks senior, lead, principal, director, head, VP and chief roles.
* Blocks roles requiring five or more years of experience.
* Prioritises assistant, coordinator, junior, associate, officer, administrator, specialist, paralegal and caseworker roles.
* Keeps realistic mid-level roles, but penalises manager titles unless the overall opportunity is strong.
* Revalidates and quarantines unsuitable jobs already stored in the database.
* Preserves the permanent applicant profile and Google OAuth authorization across upgrades.

## Launch sequence

1. Run `install.bat`.
2. Run `start_vocanta.bat`.
3. Press `A` for automated applications.

Do not run profile or Gmail setup again unless you are changing those settings.
