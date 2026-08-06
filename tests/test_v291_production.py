import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.database import Database
from core.models import Job
from intelligence.eligibility import assess_eligibility, discovery_only_reason
from notifications.emailer import AUTH_MODE_OAUTH, load_email_settings


class V291ProductionTests(unittest.TestCase):
    def test_remoteok_is_discovery_only(self):
        job = Job(
            company="Example",
            title="Executive Assistant",
            location="Worldwide",
            source="RemoteOK",
            url="https://remoteok.com/remote-jobs/example",
            description="Worldwide remote role",
            score=95,
        )
        self.assertIn("Discovery-only", discovery_only_reason(job))
        self.assertEqual(assess_eligibility(job).verdict, "BLOCK")

    def test_jobgether_company_is_discovery_only_even_on_lever(self):
        job = Job(
            company="Jobgether",
            title="People Operations Coordinator",
            location="Global",
            source="Lever",
            url="https://jobs.lever.co/jobgether/example",
            description="Global remote role",
            score=95,
        )
        self.assertIn("marketplace company", discovery_only_reason(job))

    def test_oauth_credential_is_recovered_from_legacy_service(self):
        with tempfile.TemporaryDirectory() as folder:
            settings_file = Path(folder) / "email_settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "sender_email": "Clarris@Example.com",
                        "recipient_email": "Clarris@Example.com",
                        "auth_mode": AUTH_MODE_OAUTH,
                    }
                ),
                encoding="utf-8",
            )

            def get_password(service, username):
                if service == "VOCANTA_EMAIL" and username == "clarris@example.com":
                    return "legacy-oauth-token"
                return None

            with patch("notifications.emailer.EMAIL_SETTINGS_FILE", settings_file), \
                 patch("notifications.emailer.LEGACY_EMAIL_SETTINGS_FILE", Path(folder) / "none.json"), \
                 patch("notifications.emailer.keyring.get_password", side_effect=get_password), \
                 patch("notifications.emailer.keyring.set_password") as repair:
                loaded = load_email_settings()

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded[1], "legacy-oauth-token")
            repair.assert_called_with(
                "VOCANTA_GOOGLE_OAUTH",
                "clarris@example.com",
                "legacy-oauth-token",
            )

    def test_unsent_notification_can_be_reclaimed_for_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Database(Path(folder) / "vocanta.db")
            try:
                job = Job(
                    company="Example",
                    title="Executive Assistant",
                    location="Worldwide",
                    source="Greenhouse",
                    url="https://boards.greenhouse.io/example/jobs/1",
                    description="Worldwide remote role",
                    score=95,
                )
                database.upsert_job(job)
                row = database.connection.execute("SELECT id FROM jobs").fetchone()
                _, claimed = database.claim_notification_delivery(
                    row["id"], "retry-key", "OAUTH"
                )
                self.assertTrue(claimed)
                database.update_notification_delivery("retry-key", "SENDING")
                database.update_notification_delivery(
                    "retry-key", "OUTBOX", error_code="DELIVERY_FAILED"
                )
                retried, claimed_again = database.claim_notification_delivery(
                    row["id"], "retry-key", "OAUTH"
                )
                self.assertTrue(claimed_again)
                self.assertEqual(retried["status"], "QUEUED")
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
