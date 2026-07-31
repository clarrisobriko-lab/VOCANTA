from rich.console import Console
from rich.panel import Panel

from notifications.emailer import load_email_settings
from notifications.outbox import retry_email_outbox


def main() -> int:
    console = Console()
    configured = load_email_settings()
    if not configured:
        console.print(
            Panel(
                "Email is not connected. Run setup_email.bat first.",
                title="Outbox Retry Stopped",
                border_style="red",
            )
        )
        return 1
    settings, credential = configured
    result = retry_email_outbox(settings, credential)
    console.print(
        Panel(
            f"Drafts found: {result.attempted}\n"
            f"Sent: {result.sent}\n"
            f"Still pending: {result.failed}\n"
            f"Sent archive: {result.sent_directory or 'No files moved'}",
            title="Email Outbox Retry",
            border_style="green" if result.failed == 0 else "yellow",
        )
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
