import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.database import Database
from migrate_previous import inspect_database, version_from_path


class V296ProductionTests(unittest.TestCase):
    def test_numeric_version_parsing(self):
        newer = version_from_path(Path(r"C:/Users/test/Downloads/VOCANTA_v2.9.10/data/vocanta.db"))
        older = version_from_path(Path(r"C:/Users/test/Downloads/VOCANTA_v2.9.5/data/vocanta.db"))
        self.assertGreater(newer, older)

    def test_database_validation_rejects_missing_jobs_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vocanta.db"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE other(id INTEGER)")
            connection.close()
            valid, count, reason = inspect_database(path)
            self.assertFalse(valid)
            self.assertEqual(count, 0)
            self.assertIn("jobs table", reason)

    def test_primary_reason_is_added_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vocanta.db"
            db = Database(path)
            columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(job_intelligence)")}
            self.assertIn("primary_reason", columns)
            db.close()
            db = Database(path)
            columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(job_intelligence)")}
            self.assertIn("primary_reason", columns)
            db.close()


if __name__ == "__main__":
    unittest.main()
