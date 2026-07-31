import unittest
from unittest.mock import patch

import doctor


class DoctorTests(unittest.TestCase):
    def test_dependency_check_reports_missing_module(self):
        with patch("doctor.importlib.import_module", side_effect=ModuleNotFoundError("missing")):
            check = doctor._dependency_check("not_real")
        self.assertFalse(check.passed)
        self.assertTrue(check.required)

    def test_sqlite_health_check_passes(self):
        self.assertTrue(doctor._sqlite_check().passed)

    def test_python_requirement_is_present(self):
        checks = doctor.run_checks()
        python_check = next(check for check in checks if check.name == "python")
        self.assertTrue(python_check.passed)
