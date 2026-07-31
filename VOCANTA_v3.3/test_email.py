from email.message import EmailMessage

from rich.console import Console
from rich.panel import Panel

from notifications.emailer import deliver_message, load_email_settings


def main() -> int:
    console = Console()
    configured = load_email_settings()

    if not configured:
        console.print(
            Panel(
                "No reusable Gmail credential was found. Run setup_email.bat.",
                title="Email Test Failed",
                border_style="red",
            )
        )
        return 1

    settings, credential = configured

    message = EmailMessage()
    message["From"] = settings.sender_email
    message["To"] = settings.recipient_email
    message["Subject"] = "VOCANTA test email"
    message.set_content(
        "VOCANTA successfully retrieved the saved Windows credential "
        "and delivered this test email."
    )

    try:
        deliver_message(settings, credential, message)
    except Exception as exc:
        console.print(
            Panel(
                f"{type(exc).__name__}: {exc}",
                title="Email Test Failed",
                border_style="red",
            )
        )
        return 1

    console.print(
        Panel(
            f"Test email sent to {settings.recipient_email}.\n"
            "The saved credential is working.",
            title="Email Test Passed",
            border_style="green",
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
