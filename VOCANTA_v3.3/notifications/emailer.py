import hashlib
import json
import logging
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

import keyring

from config.settings import (
    EMAIL_CREDENTIAL_SERVICE,
    EMAIL_OUTBOX_DIR,
    EMAIL_SETTINGS_FILE,
    GOOGLE_OAUTH_CREDENTIAL_SERVICE,
    HUMAN_ACTION_RECIPIENT,
    LEGACY_EMAIL_SETTINGS_FILE,
    USER_DATA_DIR,
)
from notifications.oauth import (
    OAuthAuthorizationError,
    OAuthDependencyError,
    OAuthError,
    send_gmail_message,
)

logger = logging.getLogger(__name__)

AUTH_MODE_OAUTH = "OAUTH"
AUTH_MODE_APP_PASSWORD = "APP_PASSWORD"
DELIVERY_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class EmailSettings:
    sender_email: str
    recipient_email: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    auth_mode: str = AUTH_MODE_APP_PASSWORD


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    delivered: bool
    method: str
    location: str
    message: str
    error_code: str = ""


def _credential_service(auth_mode: str) -> str:
    return (
        GOOGLE_OAUTH_CREDENTIAL_SERVICE
        if auth_mode.strip().upper() == AUTH_MODE_OAUTH
        else EMAIL_CREDENTIAL_SERVICE
    )


def _candidate_legacy_settings_files() -> tuple[Path, ...]:
    candidates: list[Path] = [LEGACY_EMAIL_SETTINGS_FILE]
    home = Path.home()
    roots = (home / "Downloads", home / "Desktop", home / "Documents")
    for root in roots:
        if not root.is_dir():
            continue
        try:
            candidates.extend(root.glob("VOCANTA_v*/**/data/email_settings.json"))
            candidates.extend(root.glob("VOCANTA*/**/data/email_settings.json"))
        except OSError:
            continue

    unique: dict[str, Path] = {}
    current = EMAIL_SETTINGS_FILE.resolve()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved == current or not resolved.is_file():
            continue
        unique[str(resolved).lower()] = resolved
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: item.stat().st_mtime if item.exists() else 0,
            reverse=True,
        )
    )


def _valid_settings_payload(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    sender = str(payload.get("sender_email", "")).strip()
    if not sender or "@" not in sender:
        return None
    return payload


def _migrate_legacy_settings() -> None:
    if EMAIL_SETTINGS_FILE.is_file():
        return
    for candidate in _candidate_legacy_settings_files():
        payload = _valid_settings_payload(candidate)
        if payload is None:
            continue
        try:
            EMAIL_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            EMAIL_SETTINGS_FILE.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "Migrated email settings to persistent location | source=%s | target=%s",
                candidate,
                EMAIL_SETTINGS_FILE,
            )
            return
        except OSError as exc:
            logger.exception(
                "Could not migrate email settings from %s: %s",
                candidate,
                exc,
            )


def _credential_candidates(auth_mode: str, sender: str) -> tuple[tuple[str, str], ...]:
    current_service = _credential_service(auth_mode)
    sender_variants = tuple(
        dict.fromkeys(
            value
            for value in (sender, sender.lower(), sender.strip(), sender.strip().lower())
            if value
        )
    )
    services = [current_service]
    # Earlier VOCANTA builds sometimes stored OAuth data under the SMTP service.
    if auth_mode == AUTH_MODE_OAUTH:
        services.append(EMAIL_CREDENTIAL_SERVICE)
    else:
        services.append(GOOGLE_OAUTH_CREDENTIAL_SERVICE)
    return tuple((service, username) for service in dict.fromkeys(services) for username in sender_variants)


def _load_credential(auth_mode: str, sender: str) -> tuple[str | None, str, str]:
    for service, username in _credential_candidates(auth_mode, sender):
        try:
            credential = keyring.get_password(service, username)
        except Exception as exc:
            logger.exception(
                "Credential Manager lookup failed | service=%s | username=%s | error=%s",
                service,
                username,
                exc,
            )
            continue
        if credential:
            return credential, service, username
    return None, "", ""


def save_email_settings(settings: EmailSettings, credential: str) -> None:
    sender = settings.sender_email.strip().lower()
    recipient = settings.recipient_email.strip().lower()
    normalized = EmailSettings(
        sender_email=sender,
        recipient_email=recipient,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        auth_mode=settings.auth_mode.strip().upper(),
    )
    EMAIL_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_SETTINGS_FILE.write_text(
        json.dumps(
            {
                "sender_email": normalized.sender_email,
                "recipient_email": normalized.recipient_email,
                "smtp_host": normalized.smtp_host,
                "smtp_port": normalized.smtp_port,
                "auth_mode": normalized.auth_mode,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    keyring.set_password(
        _credential_service(normalized.auth_mode),
        normalized.sender_email,
        credential.strip(),
    )
    logger.info(
        "Saved persistent email configuration | sender=%s | recipient=%s | mode=%s | file=%s",
        normalized.sender_email,
        normalized.recipient_email,
        normalized.auth_mode,
        EMAIL_SETTINGS_FILE,
    )


def load_email_settings() -> tuple[EmailSettings, str] | None:
    _migrate_legacy_settings()
    if not EMAIL_SETTINGS_FILE.is_file():
        logger.error(
            "Email configuration missing | expected=%s | searched_legacy_locations=%s",
            EMAIL_SETTINGS_FILE,
            len(_candidate_legacy_settings_files()),
        )
        return None
    try:
        data = json.loads(EMAIL_SETTINGS_FILE.read_text(encoding="utf-8"))
        sender = str(data["sender_email"]).strip().lower()
        recipient = str(data.get("recipient_email") or HUMAN_ACTION_RECIPIENT or sender).strip().lower()
        auth_mode = str(data.get("auth_mode", AUTH_MODE_APP_PASSWORD)).strip().upper()
        smtp_host = str(data.get("smtp_host", "smtp.gmail.com"))
        smtp_port = int(data.get("smtp_port", 465))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        logger.exception("Email configuration is unreadable: %s", exc)
        return None
    if auth_mode not in {AUTH_MODE_OAUTH, AUTH_MODE_APP_PASSWORD}:
        logger.error("Unsupported email auth mode: %s", auth_mode)
        return None

    credential, found_service, found_username = _load_credential(auth_mode, sender)
    if not sender or not recipient or not credential:
        logger.error(
            "Email credential unavailable | sender=%s | recipient=%s | mode=%s | "
            "expected_service=%s | credential_found=%s | settings_file=%s | user_data=%s",
            sender,
            recipient,
            auth_mode,
            _credential_service(auth_mode),
            bool(credential),
            EMAIL_SETTINGS_FILE,
            USER_DATA_DIR,
        )
        return None

    expected_service = _credential_service(auth_mode)
    if found_service != expected_service or found_username != sender:
        try:
            keyring.set_password(expected_service, sender, credential)
            logger.info(
                "Repaired credential location | old_service=%s | old_username=%s | new_service=%s | new_username=%s",
                found_service,
                found_username,
                expected_service,
                sender,
            )
        except Exception:
            logger.exception("Loaded credential but could not repair its persistent location")

    logger.info(
        "Loaded persistent email configuration | sender=%s | recipient=%s | mode=%s | service=%s",
        sender,
        recipient,
        auth_mode,
        found_service or expected_service,
    )
    return EmailSettings(sender, recipient, smtp_host, smtp_port, auth_mode), credential


def notification_dedup_key(
    *,
    job_id: int,
    status: str,
    recipient: str,
    attachments: Iterable[Path],
) -> str:
    digest = hashlib.sha256()
    digest.update(
        f"human_completion|{job_id}|{status}|{recipient.lower()}".encode()
    )
    for path in attachments:
        digest.update(str(path).encode())
        if path and path.is_file():
            with path.open("rb") as attachment:
                for chunk in iter(lambda: attachment.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _attach_files(message: EmailMessage, paths: Iterable[Path]) -> None:
    for path in paths:
        if not path or not path.is_file():
            continue
        data = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            maintype, subtype = "application", "pdf"
        elif suffix == ".docx":
            maintype, subtype = (
                "application",
                "vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        elif suffix in {".png", ".jpg", ".jpeg"}:
            maintype, subtype = "image", "png" if suffix == ".png" else "jpeg"
        else:
            maintype, subtype = "application", "octet-stream"
        message.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )


def _write_eml(message: EmailMessage, job_id: int) -> Path:
    EMAIL_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    path = EMAIL_OUTBOX_DIR / f"job_{job_id}_human_completion.eml"
    path.write_bytes(bytes(message))
    return path


def deliver_message(
    settings: EmailSettings,
    credential: str,
    message: EmailMessage,
) -> str:
    if settings.auth_mode == AUTH_MODE_OAUTH:
        message_id, updated_credentials = send_gmail_message(credential, message)
        try:
            keyring.set_password(
                GOOGLE_OAUTH_CREDENTIAL_SERVICE,
                settings.sender_email.lower(),
                updated_credentials,
            )
        except Exception:
            logger.exception(
                "Email sent, but refreshed OAuth token could not be persisted"
            )
        return message_id
    with smtplib.SMTP_SSL(
        settings.smtp_host,
        settings.smtp_port,
        timeout=30,
    ) as smtp:
        smtp.login(settings.sender_email, credential)
        smtp.send_message(message)
    return "smtp"


def send_human_completion_email(
    *,
    job_id: int,
    company: str,
    title: str,
    job_url: str,
    status: str,
    reason: str,
    score: int,
    opportunity_score: int,
    recommendation: str,
    sponsorship: str,
    relocation: str,
    rationale: str,
    attachments: Iterable[Path],
) -> DeliveryResult:
    attachment_list = tuple(attachments)
    configured = load_email_settings()
    recipient = (
        configured[0].recipient_email
        if configured
        else HUMAN_ACTION_RECIPIENT or "applicant@example.com"
    )
    sender = configured[0].sender_email if configured else recipient
    subject = f"[VOCANTA ACTION REQUIRED] {company} · {title}"
    body = (
        "VOCANTA has paused an application that requires your input.\n\n"
        f"Company: {company}\n"
        f"Role: {title}\n"
        f"Job score: {score}\n"
        f"Opportunity score: {opportunity_score}\n"
        f"Recommended track: {recommendation}\n"
        f"Visa signal: {sponsorship}\n"
        f"Relocation signal: {relocation}\n"
        f"Status: {status}\n"
        f"Reason: {reason}\n\n"
        f"Assessment:\n{rationale}\n\n"
        f"Open and complete the application:\n{job_url}\n\n"
        "The tailored CV, cover letter, certificate and current browser "
        "screenshot available for this application are attached.\n"
    )
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = (
        sender,
        recipient,
        subject,
    )
    message.set_content(body)
    _attach_files(message, attachment_list)

    if configured:
        settings, credential = configured
        last_exc: Exception | None = None
        for attempt in range(1, DELIVERY_ATTEMPTS + 1):
            try:
                message_id = deliver_message(settings, credential, message)
                logger.info(
                    "Human-action notification sent | job_id=%s | attempt=%s | recipient=%s | message_id=%s",
                    job_id,
                    attempt,
                    settings.recipient_email,
                    message_id,
                )
                return DeliveryResult(
                    True,
                    settings.auth_mode,
                    settings.recipient_email,
                    f"Human-action email sent on attempt {attempt}.",
                )
            except (OAuthAuthorizationError, smtplib.SMTPAuthenticationError) as exc:
                last_exc = exc
                logger.exception(
                    "Email authorization failed | job_id=%s | attempt=%s",
                    job_id,
                    attempt,
                )
                break
            except (OAuthDependencyError, OAuthError, OSError, smtplib.SMTPException) as exc:
                last_exc = exc
                logger.exception(
                    "Email delivery attempt failed | job_id=%s | attempt=%s/%s",
                    job_id,
                    attempt,
                    DELIVERY_ATTEMPTS,
                )
                if attempt < DELIVERY_ATTEMPTS:
                    time.sleep(attempt)
        eml = _write_eml(message, job_id)
        auth_error = isinstance(
            last_exc,
            (OAuthAuthorizationError, smtplib.SMTPAuthenticationError),
        )
        return DeliveryResult(
            False,
            "OUTBOX",
            str(eml),
            "Email delivery failed after retries; draft saved. Exact error: "
            f"{type(last_exc).__name__}: {last_exc}",
            "AUTH_REQUIRED" if auth_error else "DELIVERY_FAILED",
        )

    eml = _write_eml(message, job_id)
    logger.error(
        "Human-action notification not sent because persistent email configuration "
        "was not loaded | job_id=%s | settings=%s",
        job_id,
        EMAIL_SETTINGS_FILE,
    )
    return DeliveryResult(
        False,
        "OUTBOX",
        str(eml),
        "Persistent email configuration or Credential Manager authorization was "
        f"not found. Draft saved at {eml}.",
        "NOT_CONFIGURED",
    )
