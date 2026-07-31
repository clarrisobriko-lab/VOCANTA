import tempfile
import unittest
from pathlib import Path

from core.database import Database


def create_legacy_database(path: Path) -> None:
    database = Database(path)
    try:
        database.connection.execute(
            """
            INSERT INTO jobs(
                company, title, location, source, url, description,
                salary, employment_type, score, status, applied,
                applied_date, follow_up_date, notes, first_seen_at,
                last_seen_at, updated_at
            )
            VALUES(
                'Canonical',
                'Executive Assistant',
                'Remote',
                'Greenhouse',
                'https://example.test/job',
                '',
                '',
                '',
                90,
                'APPLIED',
                1,
                '2026-07-13T10:11:18+00:00',
                NULL,
                'Interested in feedback',
                '2026-07-13T09:00:00+00:00',
                '2026-07-13T10:00:00+00:00',
                '2026-07-13T10:11:18+00:00'
            )
            """
        )
        database.connection.execute("DELETE FROM application_history")
        database.connection.commit()
    finally:
        database.close()


class HistoryTests(unittest.TestCase):
    def test_history_backfill_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            database_file = Path(directory) / "vocanta.db"
            create_legacy_database(database_file)
            database = Database(database_file)
            try:
                history = database.get_history(1)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["old_status"], "IMPORTED")
                self.assertEqual(history[0]["new_status"], "APPLIED")
                self.assertEqual(history[0]["notes"], "Interested in feedback")
                self.assertEqual(database.repair_history(), 0)
                self.assertEqual(len(database.get_history(1)), 1)
            finally:
                database.close()

    def test_update_application_writes_history(self):
        with tempfile.TemporaryDirectory() as directory:
            database_file = Path(directory) / "vocanta.db"
            create_legacy_database(database_file)
            database = Database(database_file)
            try:
                database.update_application(
                    1,
                    "INTERVIEW",
                    "Interview booked",
                    None,
                )
                history = database.get_history(1)
                self.assertEqual(len(history), 2)
                self.assertEqual(history[0]["old_status"], "APPLIED")
                self.assertEqual(history[0]["new_status"], "INTERVIEW")
                self.assertEqual(history[0]["notes"], "Interview booked")
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
