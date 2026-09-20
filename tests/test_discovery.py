# tests/test_discovery.py
import threading
import unittest
from wfprint import config, discovery


class MappingTest(unittest.TestCase):
    def test_build_multi_mapping_ports(self):
        m = config.build_multi_mapping(["HP A", "Epson B"])
        self.assertEqual(m, {9100: "HP A", 9101: "Epson B"})

    def test_build_multi_mapping_custom_base(self):
        self.assertEqual(config.build_multi_mapping(["X"], base=9110), {9110: "X"})

    def test_build_multi_mapping_empty(self):
        self.assertEqual(config.build_multi_mapping([]), {})


class DiscoverTest(unittest.TestCase):
    def test_loopback_roundtrip(self):
        stop = threading.Event()
        mapping = {9100: "HP Test"}
        t = threading.Thread(target=discovery.responder, args=(mapping, "127.0.0.1", stop),
                             kwargs={"port": 19107}, daemon=True)
        t.start()
        try:
            found = discovery.discover(timeout=1.5, port=19107, targets=["127.0.0.1"])
            ips = [ip for ip, _ in found]
            self.assertIn("127.0.0.1", ips)
            for ip, printers in found:
                if ip == "127.0.0.1":
                    self.assertEqual(printers, {"9100": "HP Test"})
        finally:
            stop.set()

    def test_no_server_empty(self):
        found = discovery.discover(timeout=0.5, port=19108)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
