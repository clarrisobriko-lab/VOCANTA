import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from notifications.emailer import AUTH_MODE_OAUTH, EmailSettings, load_email_settings


class V29NotificationTests(unittest.TestCase):
    def test_legacy_email_settings_migrate_to_persistent_location(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            persistent = root / "persistent" / "email_settings.json"
            legacy = root / "old_release" / "email_settings.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({
                "sender_email": "clarris@example.com",
                "recipient_email": "clarris@example.com",
                "auth_mode": AUTH_MODE_OAUTH,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 465,
            }), encoding="utf-8")
            with patch("notifications.emailer.EMAIL_SETTINGS_FILE", persistent), \
                 patch("notifications.emailer.LEGACY_EMAIL_SETTINGS_FILE", legacy), \
                 patch("notifications.emailer.keyring.get_password", return_value="token"):
                loaded = load_email_settings()
            self.assertIsNotNone(loaded)
            self.assertTrue(persistent.is_file())
            self.assertEqual(loaded[0].recipient_email, "clarris@example.com")

    def test_persistent_oauth_configuration_loads(self):
        with tempfile.TemporaryDirectory() as folder:
            settings_file = Path(folder) / "email_settings.json"
            settings_file.write_text(json.dumps({
                "sender_email": "clarris@example.com",
                "recipient_email": "clarris@example.com",
                "auth_mode": AUTH_MODE_OAUTH,
            }), encoding="utf-8")
            with patch("notifications.emailer.EMAIL_SETTINGS_FILE", settings_file), \
                 patch("notifications.emailer.LEGACY_EMAIL_SETTINGS_FILE", Path(folder) / "none.json"), \
                 patch("notifications.emailer.keyring.get_password", return_value="credential"):
                loaded = load_email_settings()
            self.assertEqual(loaded, (EmailSettings("clarris@example.com", "clarris@example.com", auth_mode=AUTH_MODE_OAUTH), "credential"))


if __name__ == "__main__":
    unittest.main()
