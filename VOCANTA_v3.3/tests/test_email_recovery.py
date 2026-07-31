import smtplib
import sys
import types
import unittest
from unittest.mock import patch

fake_keyring = types.SimpleNamespace(
    get_password=lambda service, username: None,
    set_password=lambda service, username, password: None,
)
sys.modules.setdefault("keyring", fake_keyring)
fake_rich_console = types.ModuleType("rich.console")
fake_rich_console.Console = type(
    "Console",
    (),
    {"print": lambda self, *args, **kwargs: None},
)
fake_rich_panel = types.ModuleType("rich.panel")
fake_rich_panel.Panel = lambda *args, **kwargs: args[0] if args else ""
sys.modules.setdefault("rich", types.ModuleType("rich"))
sys.modules.setdefault("rich.console", fake_rich_console)
sys.modules.setdefault("rich.panel", fake_rich_panel)

import setup_email
from notifications.emailer import AUTH_MODE_APP_PASSWORD, EmailSettings


class EmailRecoveryTests(unittest.TestCase):
    def test_app_password_whitespace_is_removed(self):
        self.assertEqual(
            setup_email.normalize_app_password("abcd efgh\nijkl mnop"),
            "abcdefghijklmnop",
        )

    def test_default_setup_dispatches_to_oauth(self):
        with patch("setup_email.oauth_main", return_value=0) as oauth_main:
            result = setup_email.main([])
        self.assertEqual(result, 0)
        oauth_main.assert_called_once()

    def test_explicit_legacy_mode_dispatches_to_app_password(self):
        with patch(
            "setup_email.app_password_main",
            return_value=0,
        ) as app_password_main:
            result = setup_email.main(["--app-password"])
        self.assertEqual(result, 0)
        app_password_main.assert_called_once()

    def test_failed_replacement_does_not_overwrite_credential(self):
        settings = EmailSettings(
            sender_email="applicant@example.com",
            recipient_email="reviewer@example.com",
            auth_mode=AUTH_MODE_APP_PASSWORD,
        )
        with patch(
            "setup_email.load_email_settings",
            return_value=(settings, "invalid-password"),
        ), patch(
            "setup_email.send_test_email",
            side_effect=[
                smtplib.SMTPAuthenticationError(535, b"bad credentials"),
                smtplib.SMTPAuthenticationError(535, b"bad replacement"),
            ],
        ), patch(
            "setup_email.getpass",
            return_value="bad replacement",
        ), patch("setup_email.save_email_settings") as save_settings:
            result = setup_email.app_password_main(
                fake_rich_console.Console()
            )
        self.assertEqual(result, 1)
        save_settings.assert_not_called()


if __name__ == "__main__":
    unittest.main()
