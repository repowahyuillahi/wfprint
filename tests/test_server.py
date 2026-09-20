# tests/test_server.py
import socket
import unittest
from wfprint import server
from wfprint import spool


class RecvTest(unittest.TestCase):
    def test_recv_until_fin(self):
        a, b = socket.socketpair()
        try:
            b.sendall(b"HELLO" * 1000)
            b.shutdown(socket.SHUT_WR)
            data = server.recv_job(a, timeout=2.0)
            self.assertEqual(data, b"HELLO" * 1000)
        finally:
            a.close()
            b.close()

    def test_empty_job_returns_empty(self):
        a, b = socket.socketpair()
        try:
            b.shutdown(socket.SHUT_WR)
            self.assertEqual(server.recv_job(a, timeout=2.0), b"")
        finally:
            a.close()
            b.close()

    def test_fifo_no_interleave(self):
        s = spool.FakeSpool()
        a1, b1 = socket.socketpair()
        a2, b2 = socket.socketpair()
        b1.sendall(b"AAAA-JOB1")
        b1.shutdown(socket.SHUT_WR)
        b2.sendall(b"BBBB-JOB2")
        b2.shutdown(socket.SHUT_WR)
        server.handle_conn(a1, ("c1", 1), 9100, "P1", s)
        server.handle_conn(a2, ("c2", 2), 9100, "P2", s)
        a1.close()
        a2.close()
        b1.close()
        b2.close()
        blob = b"".join(s.jobs.values())
        self.assertIn(b"AAAA-JOB1", blob)
        self.assertIn(b"BBBB-JOB2", blob)


class CountingSpool(spool.FakeSpool):
    def __init__(self):
        super().__init__()
        self.opens = 0

    def open(self, name):
        self.opens += 1
        return super().open(name)


class AbortTrackSpool(spool.FakeSpool):
    def __init__(self):
        super().__init__()
        self.aborted = False
        self.last_handle = None

    def open(self, name):
        h = super().open(name)
        self.last_handle = h
        return h

    def abort(self, handle):
        self.aborted = True
        super().abort(handle)


class StreamTest(unittest.TestCase):
    def test_empty_job_never_opens_spooler(self):
        s = CountingSpool()
        a, b = socket.socketpair()
        try:
            b.shutdown(socket.SHUT_WR)
            rc = server.handle_conn(a, ("c", 1), 9100, "P", s)
            self.assertEqual(rc, 0)
            self.assertEqual(s.opens, 0)
        finally:
            a.close()
            b.close()

    def test_midjob_timeout_aborts_and_returns_zero(self):
        s = AbortTrackSpool()
        a, b = socket.socketpair()
        try:
            b.sendall(b"PART")
            rc = server.handle_conn(a, ("c", 1), 9100, "P", s, timeout=0.3)
            self.assertEqual(rc, 0)
            self.assertTrue(s.aborted)
            self.assertEqual(s.jobs.get(s.last_handle, b""), b"PART")
        finally:
            a.close()
            b.close()

    def test_second_bind_failure_closes_cleanly(self):
        import threading
        held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        held.bind(("127.0.0.1", 0))
        occ = held.getsockname()[1]
        held.listen(1)
        try:
            stop = threading.Event()
            stop.set()
            with self.assertRaises(SystemExit) as cm:
                server.serve({0: "P1", occ: "P2"}, "127.0.0.1", spool.FakeSpool, stop)
            self.assertEqual(cm.exception.code, 2)
        finally:
            held.close()


if __name__ == "__main__":
    unittest.main()
