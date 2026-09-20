# tests/test_config.py
import os
import shutil
import tempfile
import unittest
from wfprint import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self._old_appdata = os.environ.get("APPDATA")
        self._tmp = tempfile.mkdtemp(prefix="wfprint-test-")
        os.environ["APPDATA"] = self._tmp

    def tearDown(self):
        if self._old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old_appdata
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_config_lives_under_appdata(self):
        self.assertTrue(str(config.config_file()).startswith(self._tmp))

    def test_save_then_load_roundtrip(self):
        m = {"9100": "HP LaserJet Pro M12w"}
        config.save_config(m)
        self.assertEqual(config.load_config(), m)

    def test_load_missing_returns_empty(self):
        p = config.config_file()
        if os.path.exists(p):
            os.remove(p)
        self.assertEqual(config.load_config(), {})

    def test_apply_cli_merges_and_prefers_cli(self):
        saved = {"9100": "Lama", "9101": "Tetap"}
        merged = config.apply_cli(saved, 9100, "Baru")
        self.assertEqual(merged, {"9100": "Baru", "9101": "Tetap"})

    def test_apply_cli_empty_printer_keeps_saved(self):
        saved = {"9100": "Lama"}
        self.assertEqual(config.apply_cli(saved, 9100, ""), {"9100": "Lama"})


if __name__ == "__main__":
    unittest.main()
