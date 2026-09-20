# tests/test_gui.py
import unittest
from wfprint import gui


class ValidateTest(unittest.TestCase):
    def test_valid_server_inputs(self):
        errs = gui.validate_server("192.168.1.10", "9100", "HP Laser")
        self.assertEqual(errs, [])

    def test_bad_ip_rejected(self):
        errs = gui.validate_server("999.1.1.1", "9100", "HP")
        self.assertTrue(any("IP" in e for e in errs))

    def test_bad_port_rejected(self):
        self.assertTrue(gui.validate_server("192.168.1.10", "abc", "HP"))
        self.assertTrue(gui.validate_server("192.168.1.10", "0", "HP"))
        self.assertTrue(gui.validate_server("192.168.1.10", "70000", "HP"))

    def test_empty_printer_rejected(self):
        errs = gui.validate_server("192.168.1.10", "9100", "  ")
        self.assertTrue(any("printer" in e.lower() for e in errs))

    def test_build_mapping_int_key(self):
        self.assertEqual(gui.build_mapping("9100", "HP"), {9100: "HP"})

    def test_valid_client_inputs(self):
        errs = gui.validate_client("192.168.1.10", "9100", "Kantor", "Driver X")
        self.assertEqual(errs, [])

    def test_client_setup_needs_driver(self):
        errs = gui.validate_client("192.168.1.10", "9100", "Kantor", "  ")
        self.assertTrue(any("driver" in e.lower() for e in errs))


if __name__ == "__main__":
    unittest.main()
