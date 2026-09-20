import socket
import subprocess


def probe(host: str, port: int, timeout: float = 3.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, int(port)))
        return True
    except OSError:
        return False
    finally:
        s.close()


def ps_setup(port_name: str, host: str, port: int, printer_name: str, driver_name: str) -> str:
    pn = printer_name.replace('"', '')
    dn = driver_name.replace('"', '')
    return (
        f'Add-PrinterPort -Name "{port_name}" -PrinterHostAddress "{host}" -PortNumber {int(port)}\n'
        f'Add-Printer -Name "{pn}" -DriverName "{dn}" -PortName "{port_name}"\n'
    )


def setup(host: str, port: int, printer_name: str, driver_name: str) -> int:
    if not probe(host, port):
        print("FAIL: cek IP/port, firewall server, wfprint --server jalan")
        return 1
    port_name = f"TCP-{host}-{int(port)}"
    ps = ps_setup(port_name, host, port, printer_name, driver_name)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
    return r.returncode


def print_test_page(printer_name: str) -> int:
    ps = f'rundll32 printui.dll,PrintUIEntry /k /n "{printer_name}"'
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return r.returncode
