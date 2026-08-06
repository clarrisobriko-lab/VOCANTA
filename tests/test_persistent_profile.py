import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import automation.profile as profile_module

class PersistentProfileTests(unittest.TestCase):
    def test_bootstrap_profile_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"applicant_profile.json"
            with patch.object(profile_module, "_legacy_profile_candidates", return_value=[]):
                profile=profile_module.load_profile(path)
            self.assertEqual(profile.full_name, "Clarris Phegor Obriko")
            self.assertTrue(path.is_file())

if __name__ == "__main__": unittest.main()
