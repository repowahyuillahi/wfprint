# tests/test_autostart.py
import unittest
from wfprint import autostart

TEST_NAME = "wfprint-test-tmp"


class AutostartTest(unittest.TestCase):
    def tearDown(self):
        autostart.disable(TEST_NAME)

    def test_enable_then_get_then_disable(self):
        autostart.disable(TEST_NAME)
        self.assertIsNone(autostart.get_command(TEST_NAME))
        autostart.enable("C:\\x\\wfprint.exe --server", TEST_NAME)
        self.assertEqual(autostart.get_command(TEST_NAME), "C:\\x\\wfprint.exe --server")
        autostart.disable(TEST_NAME)
        self.assertIsNone(autostart.get_command(TEST_NAME))


if __name__ == "__main__":
    unittest.main()
