"""Autostart via HKCU Run (stdlib winreg)."""
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_command(name: str = "wfprint") -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return str(val)
    except FileNotFoundError:
        return None


def enable(command: str, name: str = "wfprint") -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, command)


def disable(name: str = "wfprint") -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass
