import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

fake_keyring = types.SimpleNamespace(
    get_password=lambda service, username: None,
    set_password=lambda service, username, password: None,
)
sys.modules.setdefault("keyring", fake_keyring)

from notifications.emailer import (
    AUTH_MODE_OAUTH,
    EmailSettings,
    load_email_settings,
    save_email_settings,
)
from notifications.oauth import (
    OAuthConfigurationError,
    validate_desktop_client_file,
)


class EmailReuseTests(unittest.TestCase):
    def test_oauth_settings_load_from_credential_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_file = Path(directory) / "email_settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "sender_email": "applicant@example.com",
                        "recipient_email": "reviewer@example.com",
                        "auth_mode": "OAUTH",
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "notifications.emailer.EMAIL_SETTINGS_FILE",
                settings_file,
            ), patch(
                "notifications.emailer.keyring.get_password",
                return_value='{"refresh_token":"secret"}',
            ):
                configured = load_email_settings()
            self.assertIsNotNone(configured)
            settings, credential = configured
            self.assertEqual(settings.auth_mode, AUTH_MODE_OAUTH)
            self.assertEqual(settings.recipient_email, "reviewer@example.com")
            self.assertIn("refresh_token", credential)

    def test_save_oauth_uses_oauth_credential_service(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_file = Path(directory) / "email_settings.json"
            settings = EmailSettings(
                sender_email="applicant@example.com",
                recipient_email="reviewer@example.com",
                auth_mode=AUTH_MODE_OAUTH,
            )
            with patch(
                "notifications.emailer.EMAIL_SETTINGS_FILE",
                settings_file,
            ), patch(
                "notifications.emailer.keyring.set_password",
            ) as set_password:
                save_email_settings(settings, '{"token":"secret"}')
            self.assertEqual(
                json.loads(settings_file.read_text(encoding="utf-8"))[
                    "auth_mode"
                ],
                "OAUTH",
            )
            self.assertIn("VOCANTA_GOOGLE_OAUTH", set_password.call_args.args)

    def test_desktop_client_validation_rejects_web_client(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            path.write_text(
                json.dumps({"web": {"client_id": "wrong"}}),
                encoding="utf-8",
            )
            with self.assertRaises(OAuthConfigurationError):
                validate_desktop_client_file(path)


if __name__ == "__main__":
    unittest.main()
