import argparse
import logging
import os


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="wfprint")
    ap.add_argument("--server", action="store_true")
    ap.add_argument("--client", action="store_true")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--test-page", action="store_true")
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--printer", default="")
    ap.add_argument("--driver", default="")
    return ap


def _log_file() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "wfprint")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "wfprint.log")


def main(argv=None) -> int:
    ap = build_parser()
    ns = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.FileHandler(_log_file(), encoding="utf-8"),
                                  logging.StreamHandler()])
    if ns.server:
        from wfprint import config as cfg
        from wfprint import server
        from wfprint import spool
        import threading
        merged = cfg.apply_cli(cfg.load_config(), ns.port, ns.printer)
        cfg.save_config(merged)
        mapping = {int(k): v for k, v in merged.items()}
        if ns.port not in mapping:
            print(f"FAIL: port {ns.port} belum punya mapping printer. Ulangi dengan --printer \"Nama Printer\".")
            return 2
        stop = threading.Event()
        server.serve(mapping, ns.bind, spool.WinSpool, stop)
        return 0
    if ns.setup:
        from wfprint import client
        if not ns.printer or not ns.driver:
            print("FAIL: --setup butuh --printer \"Nama\" dan --driver \"Nama Driver\".")
            return 2
        return client.setup(ns.host, ns.port, ns.printer, ns.driver)
    if ns.test_page:
        from wfprint import client
        if not ns.printer:
            print("FAIL: --test-page butuh --printer \"Nama\".")
            return 2
        return client.print_test_page(ns.printer)
    if ns.client:
        from wfprint import client
        ok = client.probe(ns.host, ns.port)
        print("OK" if ok else "FAIL: cek IP/port, firewall server, wfprint --server jalan")
        return 0 if ok else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
