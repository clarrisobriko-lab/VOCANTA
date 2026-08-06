from email.message import EmailMessage
from getpass import getpass
from pathlib import Path
from shutil import copy2
import smtplib
import sys

from rich.console import Console
from rich.panel import Panel

from config.settings import (
    EMAIL_CREDENTIAL_SERVICE,
    GOOGLE_OAUTH_CLIENT_FILE,
    GOOGLE_OAUTH_CREDENTIAL_SERVICE,
    HUMAN_ACTION_RECIPIENT,
)
from notifications.emailer import (
    AUTH_MODE_APP_PASSWORD,
    AUTH_MODE_OAUTH,
    EmailSettings,
    deliver_message,
    load_email_settings,
    save_email_settings,
)
from notifications.oauth import (
    OAuthError,
    connect_google_account,
    send_gmail_message,
    validate_desktop_client_file,
)
from notifications.outbox import retry_email_outbox


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def normalize_app_password(value: str) -> str:
    return "".join(value.split())


def _test_message(sender: str, recipient: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = "VOCANTA email test successful"
    message.set_content(
        "VOCANTA successfully connected to Gmail and can send "
        "high-value applications for human completion."
    )
    return message


def send_test_email(settings: EmailSettings, credential: str) -> str:
    message = _test_message(
        settings.sender_email,
        settings.recipient_email,
    )
    if settings.auth_mode == AUTH_MODE_OAUTH:
        _message_id, updated = send_gmail_message(credential, message)
        return updated
    deliver_message(settings, credential, message)
    return credential


def install_oauth_client(source: Path | str) -> Path:
    source_path = Path(source).expanduser().resolve()
    validate_desktop_client_file(source_path)
    GOOGLE_OAUTH_CLIENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    target = GOOGLE_OAUTH_CLIENT_FILE.resolve()
    if source_path != target:
        copy2(source_path, target)
    return target


def _oauth_instructions(console: Console) -> None:
    console.print(
        Panel(
            "1. Open Google Cloud Console.\n"
            "2. Create or select a project and enable Gmail API.\n"
            "3. Configure the OAuth consent screen.\n"
            "4. Create OAuth client credentials with application type Desktop app.\n"
            "5. Download the JSON file, then run setup_email.bat again and paste "
            "its path.\n\n"
            "Google sign-in and consent happen once. VOCANTA then refreshes "
            "access automatically through Windows Credential Manager.",
            title="Google OAuth Client Required",
            border_style="yellow",
        )
    )


def oauth_main(console: Console) -> int:
    configured = load_email_settings()
    if configured and configured[0].auth_mode == AUTH_MODE_OAUTH:
        settings, credential = configured
        console.print(
            f"[cyan]Testing the saved Google connection for "
            f"{settings.sender_email}.[/cyan]"
        )
        try:
            updated = send_test_email(settings, credential)
        except Exception as exc:
            console.print(
                f"[yellow]The saved Google connection needs renewal: "
                f"{type(exc).__name__}[/yellow]"
            )
        else:
            save_email_settings(settings, updated)
            retry_result = retry_email_outbox(settings, updated)
            retry_note = (
                f"\nSaved notification drafts sent: {retry_result.sent}"
                if retry_result.attempted
                else ""
            )
            console.print(
                Panel(
                    f"Gmail OAuth connection is healthy.\n"
                    f"Test email sent to: {settings.recipient_email}\n"
                    "Future access tokens will refresh automatically."
                    f"{retry_note}",
                    title="Email Ready",
                    border_style="green",
                )
            )
            return 0

    default_recipient = (
        configured[0].recipient_email
        if configured
        else HUMAN_ACTION_RECIPIENT
    )
    recipient = ask("Human completion recipient", default_recipient)
    if not recipient or "@" not in recipient:
        console.print("[red]A valid recipient email is required.[/red]")
        return 1

    client_file = GOOGLE_OAUTH_CLIENT_FILE
    if not client_file.is_file():
        entered = ask("Path to downloaded Google Desktop OAuth JSON")
        if not entered:
            _oauth_instructions(console)
            return 1
        try:
            client_file = install_oauth_client(entered.strip('"'))
        except (OSError, OAuthError) as exc:
            console.print(
                Panel(str(exc), title="OAuth Client Invalid", border_style="red")
            )
            return 1

    console.print(
        "[cyan]Opening Google for one-time sign-in and consent.[/cyan]"
    )
    try:
        sender, credential = connect_google_account(client_file)
        settings = EmailSettings(
            sender_email=sender,
            recipient_email=recipient,
            auth_mode=AUTH_MODE_OAUTH,
        )
        updated = send_test_email(settings, credential)
    except Exception as exc:
        console.print(
            Panel(
                f"{type(exc).__name__}: {exc}\n\n"
                "The previous saved credential was not changed.",
                title="Google Connection Failed",
                border_style="red",
            )
        )
        return 1

    save_email_settings(settings, updated)
    retry_result = retry_email_outbox(settings, updated)
    retry_note = (
        f"\nSaved notification drafts sent: {retry_result.sent}"
        if retry_result.attempted
        else ""
    )
    console.print(
        Panel(
            f"Connected Google account: {sender}\n"
            f"Test email sent to: {recipient}\n"
            f"Refresh authorization stored in Windows Credential Manager: "
            f"{GOOGLE_OAUTH_CREDENTIAL_SERVICE}"
            f"{retry_note}",
            title="Email Ready",
            border_style="green",
        )
    )
    return 0


def stored_app_password(sender_email: str) -> str | None:
    return __import__("keyring").get_password(
        EMAIL_CREDENTIAL_SERVICE,
        sender_email,
    )


def replace_invalid_app_password(
    console: Console,
    sender_email: str,
    recipient_email: str,
) -> int:
    console.print(
        "[yellow]The saved App Password is invalid or revoked.[/yellow]"
    )
    replacement = normalize_app_password(
        getpass("Paste the replacement Google App Password: ")
    )
    if not replacement:
        console.print("[red]A replacement App Password is required.[/red]")
        return 1
    settings = EmailSettings(
        sender_email=sender_email,
        recipient_email=recipient_email,
        auth_mode=AUTH_MODE_APP_PASSWORD,
    )
    try:
        send_test_email(settings, replacement)
    except Exception as exc:
        console.print(
            Panel(
                f"{type(exc).__name__}: {exc}\n\n"
                "The old saved credential was not changed.",
                title="Email Test Failed",
                border_style="red",
            )
        )
        return 1
    save_email_settings(settings, replacement)
    console.print(
        Panel(
            f"Replacement accepted and test sent to {recipient_email}.",
            title="Legacy Email Ready",
            border_style="green",
        )
    )
    return 0


def app_password_main(console: Console) -> int:
    configured = load_email_settings()
    if configured and configured[0].auth_mode == AUTH_MODE_APP_PASSWORD:
        settings, credential = configured
        try:
            send_test_email(settings, credential)
        except smtplib.SMTPAuthenticationError:
            return replace_invalid_app_password(
                console,
                settings.sender_email,
                settings.recipient_email,
            )
        except Exception as exc:
            console.print(
                Panel(str(exc), title="Email Test Failed", border_style="red")
            )
            return 1
        console.print("[green]Saved App Password is valid.[/green]")
        return 0

    sender = ask("Sender Gmail address")
    recipient = ask("Human completion recipient", sender)
    if "@" not in sender or "@" not in recipient:
        console.print("[red]Valid sender and recipient emails are required.[/red]")
        return 1
    credential = normalize_app_password(getpass("Gmail App Password: "))
    if not credential:
        console.print("[red]An App Password is required.[/red]")
        return 1
    settings = EmailSettings(
        sender_email=sender,
        recipient_email=recipient,
        auth_mode=AUTH_MODE_APP_PASSWORD,
    )
    try:
        send_test_email(settings, credential)
    except Exception as exc:
        console.print(
            Panel(str(exc), title="Email Test Failed", border_style="red")
        )
        return 1
    save_email_settings(settings, credential)
    console.print("[green]Legacy App Password saved and tested.[/green]")
    return 0


def main(argv: list[str] | None = None) -> int:
    console = Console()
    args = list(sys.argv[1:] if argv is None else argv)
    if "--app-password" in args:
        console.print(
            "[yellow]Legacy App Password mode selected. OAuth is recommended.[/yellow]"
        )
        return app_password_main(console)

    console.print(
        Panel(
            "VOCANTA now uses Google OAuth by default. You approve Google once; "
            "VOCANTA stores renewable authorization in Windows Credential Manager "
            "and refreshes access automatically.",
            title="VOCANTA Gmail Connection",
            border_style="cyan",
        )
    )
    return oauth_main(console)


if __name__ == "__main__":
    raise SystemExit(main())
