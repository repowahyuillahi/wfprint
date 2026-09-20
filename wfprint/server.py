import logging
import socket
import threading

RECV_TIMEOUT = 30.0
CHUNK = 65536

log = logging.getLogger("wfprint.server")
_locks: dict = {}
_locks_guard = threading.Lock()


def _lock_for(port: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(port, threading.Lock())


def recv_job(conn: socket.socket, timeout: float = RECV_TIMEOUT) -> bytes:
    conn.settimeout(timeout)
    parts = []
    try:
        while True:
            b = conn.recv(CHUNK)
            if not b:
                break
            parts.append(b)
    except socket.timeout:
        pass
    return b"".join(parts)


def _close_quiet(conn: socket.socket) -> None:
    try:
        conn.close()
    except OSError:
        pass


def handle_conn(conn: socket.socket, addr, port: int, printer_name: str, spool, timeout: float = RECV_TIMEOUT) -> int:
    from wfprint.spool import SpoolError
    conn.settimeout(timeout)
    try:
        first = conn.recv(CHUNK)
    except socket.timeout:
        log.error("recv timeout port=%s client=%s, job dibuang", port, addr)
        _close_quiet(conn)
        return 0
    except OSError as e:
        log.error("recv gagal port=%s client=%s err=%s", port, addr, e)
        _close_quiet(conn)
        return 0
    if not first:
        log.warning("empty job port=%s client=%s", port, addr)
        _close_quiet(conn)
        return 0
    lock = _lock_for(port)
    with lock:
        try:
            h = spool.open(printer_name)
        except SpoolError as e:
            log.error("%s port=%s client=%s", e, port, addr)
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            _close_quiet(conn)
            return 0
        aborted = False
        try:
            spool.start_doc(h, f"wfprint {addr[0]}:{addr[1]}")
            sent = spool.write(h, first)
            while True:
                try:
                    b = conn.recv(CHUNK)
                except socket.timeout:
                    log.error("job timeout port=%s printer=%s client=%s, %d bytes dibuang",
                              port, printer_name, addr, sent)
                    try:
                        spool.abort(h)
                        aborted = True
                    except Exception:
                        pass
                    return 0
                if not b:
                    break
                sent += spool.write(h, b)
            spool.end_doc(h)
            log.info("job ok port=%s printer=%s client=%s bytes=%d", port, printer_name, addr, sent)
            return sent
        except Exception as e:
            log.error("cetak gagal port=%s printer=%s client=%s err=%s", port, printer_name, addr, e)
            try:
                spool.abort(h)
                aborted = True
            except Exception:
                pass
            return 0
        finally:
            if not aborted:
                try:
                    spool.close(h)
                except Exception:
                    pass
            _close_quiet(conn)


def serve(mapping, bind_ip: str, spool_factory, stop_event) -> None:
    listeners = []
    for port in mapping:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((bind_ip, int(port)))
        except OSError as e:
            log.error("bind gagal %s:%s err=%s", bind_ip, port, e)
            s.close()
            for _, s0 in listeners:
                s0.close()
            raise SystemExit(2)
        s.listen(5)
        s.settimeout(0.5)
        listeners.append((int(port), s))
        log.info("listen %s:%s -> %s", bind_ip, port, mapping[port])
    spool = spool_factory()
    try:
        while not stop_event.is_set():
            for port, s in listeners:
                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    continue
                t = threading.Thread(target=handle_conn, args=(conn, addr, port, mapping[port], spool), daemon=True)
                t.start()
    finally:
        for _, s in listeners:
            s.close()
