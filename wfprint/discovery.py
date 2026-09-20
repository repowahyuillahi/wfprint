"""UDP broadcast discovery: client cari server wfprint di LAN."""
import json
import logging
import socket

log = logging.getLogger("wfprint.discovery")

DISCOVERY_PORT = 9107
MAGIC = b"WFPRINT_DISCOVER"


def responder(mapping: dict, bind_ip: str, stop_event, port: int = DISCOVERY_PORT) -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((bind_ip, port))
    except OSError as e:
        log.warning("discovery bind gagal %s:%s err=%s (TCP tetap jalan)", bind_ip, port, e)
        return
    s.settimeout(0.5)
    payload = json.dumps({"wfprint": 1,
                          "printers": {str(k): v for k, v in mapping.items()}}).encode("utf-8")
    while not stop_event.is_set():
        try:
            data, addr = s.recvfrom(1024)
        except socket.timeout:
            continue
        except OSError:
            break
        if data == MAGIC:
            try:
                s.sendto(payload, addr)
            except OSError:
                pass
    s.close()


def discover(timeout: float = 3.0, port: int = DISCOVERY_PORT, targets=None) -> list:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    for t in (targets or ["<broadcast>"]):
        try:
            s.sendto(MAGIC, (t, port))
        except OSError:
            continue
    found: dict = {}
    try:
        while True:
            try:
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(msg, dict) and msg.get("wfprint") == 1 and isinstance(msg.get("printers"), dict):
                found[addr[0]] = {str(k): str(v) for k, v in msg["printers"].items()}
    finally:
        s.close()
    return sorted(found.items())
