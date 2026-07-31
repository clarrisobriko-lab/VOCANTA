from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path

from config.settings import EMAIL_OUTBOX_DIR
from notifications.emailer import EmailSettings, deliver_message, load_email_settings


@dataclass(frozen=True, slots=True)
class OutboxRetryResult:
    attempted: int
    sent: int
    failed: int
    sent_directory: str


def retry_email_outbox(
    settings: EmailSettings,
    credential: str,
    outbox_directory: Path = EMAIL_OUTBOX_DIR,
) -> OutboxRetryResult:
    if not outbox_directory.is_dir():
        return OutboxRetryResult(0, 0, 0, "")

    sent_directory = outbox_directory / "sent"
    attempted = 0
    sent = 0
    failed = 0
    current_credential = credential

    for path in sorted(outbox_directory.glob("*.eml")):
        attempted += 1
        try:
            message = BytesParser(policy=policy.default).parsebytes(
                path.read_bytes()
            )
            deliver_message(settings, current_credential, message)
            configured = load_email_settings()
            if configured and configured[0].sender_email == settings.sender_email:
                current_credential = configured[1]
            sent_directory.mkdir(parents=True, exist_ok=True)
            path.replace(sent_directory / path.name)
            sent += 1
        except Exception:
            failed += 1

    return OutboxRetryResult(
        attempted=attempted,
        sent=sent,
        failed=failed,
        sent_directory=str(sent_directory) if sent else "",
    )
