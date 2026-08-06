from rich.console import Console
from rich.panel import Panel

from automation.profile import ApplicantProfile, save_profile
from config.settings import (
    APPLICANT_PROFILE_FILE,
    AUTOMATION_DEFAULT_COUNTRY,
    EXECUTIVE_ASSISTANT_CERTIFICATE_FILE,
    MASTER_COVER_LETTER_FILE,
    MASTER_CV_FILE,
)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_bool(prompt: str, default: bool = True) -> bool:
    default_text = "Y" if default else "N"
    value = input(f"{prompt} [Y/N, default {default_text}]: ").strip().lower()
    if not value:
        return default
    return value.startswith("y")


def main() -> int:
    console = Console()
    console.print(
        Panel(
            "Your applicant profile is stored permanently outside version folders. "
            "Run this only when you want to change your details. "
            "Your approved master CV, cover letter and Executive Assistant "
            "certificate are bundled with VOCANTA. Enter only your personal "
            "application information.",
            title="VOCANTA Applicant Profile",
        )
    )

    profile = ApplicantProfile(
        first_name=ask("First name"),
        middle_name=ask("Middle name, optional"),
        last_name=ask("Last name"),
        email=ask("Email"),
        phone=ask("Phone with country code"),
        city=ask("City"),
        country=ask("Country", AUTOMATION_DEFAULT_COUNTRY),
        address=ask("Address, optional"),
        postal_code=ask("Postal code, optional"),
        linkedin_url=ask("LinkedIn URL, optional"),
        website_url=ask("Website or portfolio URL"),
        work_authorization=ask(
            "Current work authorisation answer",
            "No, I require employer sponsorship",
        ),
        requires_sponsorship=ask_bool("Do you require visa sponsorship?", True),
        notice_period=ask("Notice period", "Immediately available"),
        salary_expectation=ask("Salary expectation, optional"),
        resume_path=str(MASTER_CV_FILE),
        cover_letter_path=str(MASTER_COVER_LETTER_FILE),
        supporting_document_path=str(EXECUTIVE_ASSISTANT_CERTIFICATE_FILE),
    )

    errors = profile.validate()
    if errors:
        console.print("[bold red]Profile not saved:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        return 1

    save_profile(profile)
    console.print(
        Panel(
            f"Profile saved: {APPLICANT_PROFILE_FILE}\n\n"
            f"Legal name: {profile.full_name}\n"
            f"Two-field form surname: {profile.employer_last_name}\n\n"
            f"Master CV: {MASTER_CV_FILE}\n"
            f"Master cover letter: {MASTER_COVER_LETTER_FILE}\n"
            f"Certificate: {EXECUTIVE_ASSISTANT_CERTIFICATE_FILE}",
            title="Application Assets Ready",
            border_style="green",
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
