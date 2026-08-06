import json
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from notifications.oauth import (
    OAuthAuthorizationError,
    send_gmail_message,
    validate_desktop_client_file,
)


class FakeRefreshError(Exception):
    pass


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": "gmail-message-1"}


class FakeSession:
    last_payload = None

    def __init__(self, credentials):
        self.credentials = credentials

    def post(self, _url, json=None, timeout=None):
        self.__class__.last_payload = json
        return FakeResponse()


class FakeCredentials:
    instance = None

    def __init__(self, *, valid=True, expired=False, refresh_token="refresh"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    @classmethod
    def from_authorized_user_info(cls, _info, scopes=None):
        return cls.instance

    def refresh(self, _request):
        self.refreshed = True
        self.valid = True
        self.expired = False

    def to_json(self):
        return json.dumps({"refresh_token": self.refresh_token, "valid": self.valid})


class OAuthTests(unittest.TestCase):
    def _imports(self):
        return (
            FakeRefreshError,
            FakeSession,
            object,
            FakeCredentials,
            object,
        )

    def test_desktop_client_file_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client",
                            "client_secret": "secret",
                            "auth_uri": "https://accounts.example/auth",
                            "token_uri": "https://accounts.example/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            payload = validate_desktop_client_file(path)
            self.assertIn("installed", payload)

    def test_expired_access_token_refreshes_before_send(self):
        credentials = FakeCredentials(valid=False, expired=True)
        FakeCredentials.instance = credentials
        message = EmailMessage()
        message["From"] = "applicant@example.com"
        message["To"] = "reviewer@example.com"
        message.set_content("test")
        with patch("notifications.oauth._google_imports", self._imports):
            message_id, updated = send_gmail_message("{}", message)
        self.assertEqual(message_id, "gmail-message-1")
        self.assertTrue(credentials.refreshed)
        self.assertIn("refresh_token", updated)
        self.assertIn("raw", FakeSession.last_payload)

    def test_revoked_refresh_token_requires_reconnect(self):
        class RevokedCredentials(FakeCredentials):
            def refresh(self, _request):
                raise FakeRefreshError("revoked")

        credentials = RevokedCredentials(valid=False, expired=True)
        FakeCredentials.instance = credentials
        message = EmailMessage()
        message.set_content("test")
        with patch("notifications.oauth._google_imports", self._imports):
            with self.assertRaises(OAuthAuthorizationError):
                send_gmail_message("{}", message)


if __name__ == "__main__":
    unittest.main()
