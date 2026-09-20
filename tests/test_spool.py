# tests/test_spool.py
import unittest
from wfprint import spool


class FakeSpoolTest(unittest.TestCase):
    def test_write_roundtrip_counts_bytes(self):
        s = spool.FakeSpool()
        h = s.open("HP LaserJet (Copy 1)")
        s.start_doc(h, "wfprint-test")
        n = s.write(h, b"ABC" * 100)
        s.end_doc(h)
        s.close(h)
        self.assertEqual(n, 300)
        self.assertEqual(s.jobs[h], b"ABC" * 100)

    def test_write_after_close_raises(self):
        s = spool.FakeSpool()
        h = s.open("P")
        s.close(h)
        with self.assertRaises(spool.SpoolError):
            s.write(h, b"x")


if __name__ == "__main__":
    unittest.main()
