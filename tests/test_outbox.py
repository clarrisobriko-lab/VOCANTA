import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from notifications.emailer import AUTH_MODE_OAUTH, EmailSettings
from notifications.outbox import retry_email_outbox


class OutboxTests(unittest.TestCase):
    def test_successful_retry_moves_draft_to_sent_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = Path(directory)
            draft = outbox / "job_347_human_completion.eml"
            message = EmailMessage()
            message["From"] = "applicant@example.com"
            message["To"] = "reviewer@example.com"
            message["Subject"] = "Action required"
            message.set_content("Complete the application")
            draft.write_bytes(bytes(message))
            settings = EmailSettings(
                sender_email="applicant@example.com",
                recipient_email="reviewer@example.com",
                auth_mode=AUTH_MODE_OAUTH,
            )
            with patch(
                "notifications.outbox.deliver_message",
                return_value="message-id",
            ), patch(
                "notifications.outbox.load_email_settings",
                return_value=(settings, "updated-token"),
            ):
                result = retry_email_outbox(
                    settings,
                    "token",
                    outbox,
                )
            self.assertEqual(result.sent, 1)
            self.assertFalse(draft.exists())
            self.assertTrue(
                (outbox / "sent" / draft.name).is_file()
            )

    def test_failed_retry_keeps_original_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = Path(directory)
            draft = outbox / "job_347_human_completion.eml"
            draft.write_text("invalid but retained", encoding="utf-8")
            settings = EmailSettings(
                sender_email="applicant@example.com",
                recipient_email="reviewer@example.com",
                auth_mode=AUTH_MODE_OAUTH,
            )
            with patch(
                "notifications.outbox.deliver_message",
                side_effect=RuntimeError("offline"),
            ):
                result = retry_email_outbox(settings, "token", outbox)
            self.assertEqual(result.failed, 1)
            self.assertTrue(draft.is_file())


if __name__ == "__main__":
    unittest.main()
