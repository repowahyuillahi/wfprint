import json
import os
from pathlib import Path

DEFAULT_PORT = 9100


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "wfprint"


def config_file() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    p = config_file()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_config(mapping: dict) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    config_file().write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def apply_cli(saved: dict, port: int, printer: str) -> dict:
    m = dict(saved)
    if printer:
        m[str(port)] = printer
    return m


def build_multi_mapping(names: list, base: int = DEFAULT_PORT) -> dict:
    return {int(base) + i: n for i, n in enumerate(names)}
