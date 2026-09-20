# tests/test_client.py
import unittest
from wfprint import client


class PsTest(unittest.TestCase):
    def test_ps_contains_tcp_port_and_driver(self):
        ps = client.ps_setup("TCP-1.2.3.4-9100", "1.2.3.4", 9100, "Kantor-HP", "HP LaserJet Pro M12w")
        self.assertIn("Add-PrinterPort", ps)
        self.assertIn("1.2.3.4", ps)
        self.assertIn("9100", ps)
        self.assertIn("Add-Printer", ps)
        self.assertIn("Kantor-HP", ps)

    def test_probe_closed_port_false(self):
        self.assertFalse(client.probe("127.0.0.1", 59999, timeout=0.5))


if __name__ == "__main__":
    unittest.main()
