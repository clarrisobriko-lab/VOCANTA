import base64
import json
from email.message import EmailMessage
from pathlib import Path


OAUTH_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
)
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class OAuthError(RuntimeError):
    pass


class OAuthDependencyError(OAuthError):
    pass


class OAuthConfigurationError(OAuthError):
    pass


class OAuthAuthorizationError(OAuthError):
    pass


def _google_imports():
    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import AuthorizedSession, Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ModuleNotFoundError as exc:
        raise OAuthDependencyError(
            "Google OAuth dependencies are not installed. Run install.bat."
        ) from exc
    return RefreshError, AuthorizedSession, Request, Credentials, InstalledAppFlow


def validate_desktop_client_file(path: Path | str) -> dict:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise OAuthConfigurationError(f"OAuth client file not found: {candidate}")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OAuthConfigurationError(
            "The OAuth client file is not valid JSON."
        ) from exc

    installed = payload.get("installed")
    if not isinstance(installed, dict):
        raise OAuthConfigurationError(
            "Use a Google OAuth client created as Desktop app, not Web application."
        )
    required = {"client_id", "client_secret", "auth_uri", "token_uri"}
    missing = sorted(required.difference(installed))
    if missing:
        raise OAuthConfigurationError(
            "OAuth client file is missing: " + ", ".join(missing)
        )
    return payload


def connect_google_account(client_file: Path | str) -> tuple[str, str]:
    validate_desktop_client_file(client_file)
    (
        _refresh_error,
        AuthorizedSession,
        _request,
        _credentials,
        InstalledAppFlow,
    ) = _google_imports()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(Path(client_file).expanduser()),
        scopes=OAUTH_SCOPES,
    )
    try:
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
            access_type="offline",
            prompt="consent",
            authorization_prompt_message=(
                "Your browser is opening for one-time Google consent."
            ),
            success_message=(
                "VOCANTA is connected to Gmail. You may close this browser tab."
            ),
        )
        session = AuthorizedSession(credentials)
        response = session.get(USERINFO_URL, timeout=30)
        response.raise_for_status()
        email = str(response.json().get("email", "")).strip().lower()
    except Exception as exc:
        raise OAuthAuthorizationError(
            f"Google authorization did not complete: {type(exc).__name__}: {exc}"
        ) from exc
    if not email or "@" not in email:
        raise OAuthAuthorizationError(
            "Google did not return the connected account email address."
        )
    return email, credentials.to_json()


def send_gmail_message(
    serialized_credentials: str,
    message: EmailMessage,
) -> tuple[str, str]:
    (
        RefreshError,
        AuthorizedSession,
        Request,
        Credentials,
        _installed_app_flow,
    ) = _google_imports()
    try:
        info = json.loads(serialized_credentials)
        credentials = Credentials.from_authorized_user_info(
            info,
            scopes=OAUTH_SCOPES,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OAuthAuthorizationError(
            "The saved Google authorization is unreadable. Reconnect Gmail."
        ) from exc

    try:
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                raise OAuthAuthorizationError(
                    "Google authorization cannot be refreshed. Reconnect Gmail."
                )

        raw_message = base64.urlsafe_b64encode(bytes(message)).decode("ascii")
        session = AuthorizedSession(credentials)
        response = session.post(
            GMAIL_SEND_URL,
            json={"raw": raw_message},
            timeout=30,
        )
        if response.status_code in {401, 403}:
            raise OAuthAuthorizationError(
                "Google authorization no longer permits Gmail delivery. "
                "Reconnect Gmail."
            )
        response.raise_for_status()
        message_id = str(response.json().get("id", "")).strip()
    except RefreshError as exc:
        raise OAuthAuthorizationError(
            "Google authorization was revoked or expired. Reconnect Gmail."
        ) from exc
    except OAuthAuthorizationError:
        raise
    except Exception as exc:
        raise OAuthError(
            f"Gmail API delivery failed: {type(exc).__name__}: {exc}"
        ) from exc

    return message_id, credentials.to_json()
