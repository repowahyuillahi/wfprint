"""GUI tkinter minimal untuk wfprint (stdlib saja)."""
import ipaddress
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


def validate_server(bind: str, port: str, printer: str) -> list:
    errs = []
    try:
        ipaddress.ip_address(bind.strip())
    except ValueError:
        errs.append("IP bind tidak valid.")
    try:
        p = int(str(port).strip())
        if not 1 <= p <= 65535:
            errs.append("Port harus 1-65535.")
    except ValueError:
        errs.append("Port harus angka 1-65535.")
    if not printer.strip():
        errs.append("Nama printer wajib diisi.")
    return errs


def validate_client(host: str, port: str, printer: str, driver: str) -> list:
    errs = validate_server(host, port, printer)
    if not driver.strip():
        errs.append("Nama driver wajib diisi untuk --setup.")
    return errs


def build_mapping(port: str, printer: str) -> dict:
    return {int(str(port).strip()): printer.strip()}


class QueueHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def emit(self, record):
        try:
            self.q.put_nowait(self.format(record))
        except queue.Full:
            pass


ACCENT = "#2563eb"
ACCENT_DARK = "#1d4ed8"
BG = "#f1f5f9"
CARD = "#ffffff"
TEXT = "#0f172a"
MUTED = "#64748b"
OK = "#15803d"
FAIL = "#dc2626"
FONT = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_MONO = ("Consolas", 9)


class App(tk.Tk):
    def __init__(self, start_minimized=False):
        super().__init__()
        self.title("wfprint")
        self.geometry("620x540")
        self.configure(bg=BG)
        self._theme()
        self.logq: queue.Queue = queue.Queue(maxsize=1000)
        self.server_thread = None
        self.server_stop = None
        self._setup_logging()
        self._menu()
        header = tk.Frame(self, bg=ACCENT, height=64)
        header.pack(fill="x")
        tk.Label(header, text="wfprint", font=FONT_TITLE, fg="white", bg=ACCENT).pack(side="left", padx=16)
        tk.Label(header, text="print server LAN", font=("Segoe UI", 10), fg="#dbeafe", bg=ACCENT).pack(side="left")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        self._server_tab(nb)
        self._client_tab(nb)
        self.after(200, self._drain_log)
        self.refresh_printers()
        if start_minimized:
            self.iconify()
            self.after(500, self.auto_boot)

    def _menu(self):
        from wfprint import autostart
        mb = tk.Menu(self)
        self.config(menu=mb)
        m_file = tk.Menu(mb, tearoff=0)
        self.var_auto = tk.BooleanVar(value=autostart.get_command() is not None)
        m_file.add_checkbutton(label="▶ Jalan saat Windows nyala", variable=self.var_auto,
                               command=self.toggle_autostart)
        m_file.add_separator()
        m_file.add_command(label="⏹ Keluar", command=self.destroy)
        mb.add_cascade(label="File", menu=m_file)
        m_pr = tk.Menu(mb, tearoff=0)
        m_pr.add_command(label="🔄 Refresh daftar printer", command=self.refresh_printers)
        m_pr.add_command(label="🖨 Daftar printer...", command=self.show_printers)
        mb.add_cascade(label="Printer", menu=m_pr)
        m_help = tk.Menu(mb, tearoff=0)
        m_help.add_command(label="ℹ Tentang", command=lambda: messagebox.showinfo(
            "wfprint", "wfprint — print server LAN pengganti SMB sharing.\nTanpa cloud, tanpa driver virtual."))
        mb.add_cascade(label="Bantuan", menu=m_help)

    def _exe_server_cmd(self):
        if getattr(sys, "frozen", False):
            exe = sys.executable
        else:
            exe = f'{sys.executable} "{os.path.abspath(sys.argv[0])}"'
        return f'{exe} --server --bind {self.e_bind.get().strip()} --port {self.e_port.get().strip()}'

    def toggle_autostart(self):
        from wfprint import autostart
        if self.var_auto.get():
            autostart.enable(self._exe_server_cmd())
        else:
            autostart.disable()

    def refresh_printers(self):
        from wfprint import spool
        try:
            names = spool.WinSpool().list_printers()
        except Exception:
            names = []
        sel = {self.e_printers.get(i) for i in self.e_printers.curselection()}
        self.e_printers.delete(0, "end")
        for n in names:
            self.e_printers.insert("end", n)
            if n in sel:
                self.e_printers.selection_set("end")

    def show_printers(self):
        names = self.e_printers.get(0, "end") or ["(tidak ada printer terinstal)"]
        messagebox.showinfo("Printer terinstal", "\n".join(f"🖨 {n}" for n in names))

    def auto_boot(self):
        from wfprint import config as cfg
        saved = cfg.load_config()
        if not saved:
            return
        self.e_port.delete(0, "end")
        self.e_port.insert(0, str(min(int(k) for k in saved)))
        for i, n in enumerate(self.e_printers.get(0, "end")):
            if n in set(saved.values()):
                self.e_printers.selection_set(i)
        errs = validate_server(self.e_bind.get(), self.e_port.get(), "x")
        if not errs and not (self.server_thread and self.server_thread.is_alive()):
            self.start_server(quiet=True)

    def _theme(self):
        st = ttk.Style(self)
        for theme in ("clam", "alt", "default"):
            if theme in st.theme_names():
                st.theme_use(theme)
                break
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        st.configure("Card.TLabel", background=CARD)
        st.configure("TButton", font=FONT, padding=8)
        st.configure("Accent.TButton", background=ACCENT, foreground="white")
        st.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", MUTED)])
        st.configure("TEntry", font=FONT, padding=6)
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(16, 8))

    def _setup_logging(self):
        h = QueueHandler(self.logq)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logging.getLogger().addHandler(h)

    def _drain_log(self):
        try:
            while True:
                self.logbox.insert("end", self.logq.get_nowait() + "\n")
                self.logbox.see("end")
        except queue.Empty:
            pass
        self.after(200, self._drain_log)

    def _server_tab(self, nb):
        outer = ttk.Frame(nb)
        nb.add(outer, text="  Server  ")
        f = ttk.Frame(outer, style="Card.TFrame", padding=12)
        f.pack(fill="both", expand=True, padx=4, pady=4)
        self.e_bind = self._row(f, 0, "IP LAN PC ini", "127.0.0.1")
        self.e_port = self._row(f, 1, "Port awal", "9100")
        ttk.Label(f, text="☑ printer yang di-share", style="Card.TLabel").grid(
            row=2, column=0, sticky="nw", padx=4, pady=4)
        listframe = ttk.Frame(f, style="Card.TFrame")
        listframe.grid(row=2, column=1, sticky="nsew", padx=4, pady=4)
        self.e_printers = tk.Listbox(listframe, selectmode="multiple", font=FONT,
                                     height=4, relief="flat", highlightthickness=1,
                                     highlightbackground=MUTED, activestyle="none")
        self.e_printers.pack(side="left", fill="both", expand=True)
        ttk.Button(listframe, text="🔄", width=3, command=self.refresh_printers).pack(side="right")
        self.status = ttk.Label(f, text="● berhenti", style="Card.TLabel", foreground=MUTED)
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
        btns = ttk.Frame(f, style="Card.TFrame")
        btns.grid(row=4, column=0, columnspan=2, pady=4)
        ttk.Button(btns, text="▶ Start", style="Accent.TButton", command=self.start_server).pack(side="left", padx=4)
        ttk.Button(btns, text="⏹ Stop", command=self.stop_server).pack(side="left", padx=4)
        self.logbox = scrolledtext.ScrolledText(f, height=11, state="normal", font=FONT_MONO,
                                                bg="#0f172a", fg="#e2e8f0",
                                                insertbackground="white", relief="flat")
        self.logbox.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=6)
        f.rowconfigure(5, weight=1)
        f.columnconfigure(1, weight=1)

    def _client_tab(self, nb):
        outer = ttk.Frame(nb)
        nb.add(outer, text="  Client  ")
        f = ttk.Frame(outer, style="Card.TFrame", padding=12)
        f.pack(fill="both", expand=True, padx=4, pady=4)
        self.c_host = self._row(f, 0, "IP server", "127.0.0.1")
        self.c_port = self._row(f, 1, "Port", "9100")
        self.c_printer = self._row(f, 2, "Nama printer", "")
        self.c_driver = self._row(f, 3, "Nama driver", "")
        self.c_status = ttk.Label(f, text="● siap", style="Card.TLabel", foreground=MUTED)
        self.c_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=6)
        btns = ttk.Frame(f, style="Card.TFrame")
        btns.grid(row=5, column=0, columnspan=2, pady=4)
        ttk.Button(btns, text="🔍 Cari server", style="Accent.TButton", command=self.cli_discover).pack(side="left", padx=4)
        ttk.Button(btns, text="Cek koneksi", command=self.cli_probe).pack(side="left", padx=4)
        ttk.Button(btns, text="Pasang printer", command=self.cli_setup).pack(side="left", padx=4)
        ttk.Button(btns, text="Test page", command=self.cli_test).pack(side="left", padx=4)
        ttk.Label(f, text="Hasil pencarian (klik untuk pilih):", style="Card.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", padx=4)
        self.c_found = tk.Listbox(f, font=FONT, height=5, relief="flat",
                                  highlightthickness=1, highlightbackground=MUTED,
                                  activestyle="none")
        self.c_found.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.c_found.bind("<<ListboxSelect>>", self.cli_pick)
        self._found = []
        f.columnconfigure(1, weight=1)

    def _row(self, parent, r, label, default):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        e = ttk.Entry(parent)
        e.insert(0, default)
        e.grid(row=r, column=1, sticky="ew", padx=4, pady=4)
        return e

    def start_server(self, quiet=False):
        if self.server_thread and self.server_thread.is_alive():
            if not quiet:
                messagebox.showinfo("wfprint", "Server sudah jalan.")
            return
        from wfprint import config as cfg
        bind, port = self.e_bind.get(), self.e_port.get()
        names = [self.e_printers.get(i) for i in self.e_printers.curselection()]
        errs = validate_server(bind, port, names[0] if names else "")
        if not names:
            errs.append("Centang minimal 1 printer yang di-share.")
        if errs:
            if not quiet:
                messagebox.showerror("wfprint", "\n".join(errs))
            return
        from wfprint import server, spool
        merged = {str(k): v for k, v in cfg.build_multi_mapping(names, base=int(port)).items()}
        cfg.save_config(merged)
        mapping = {int(k): v for k, v in merged.items()}
        self.server_stop = threading.Event()
        self.server_thread = threading.Thread(
            target=server.serve, args=(mapping, bind.strip(), spool.WinSpool, self.server_stop),
            daemon=True)
        self.server_thread.start()
        ports = ",".join(str(k) for k in sorted(mapping))
        self.status.config(text=f"● jalan {len(mapping)} printer di port {ports}", foreground=OK)

    def stop_server(self):
        if self.server_stop:
            self.server_stop.set()
        self.status.config(text="● berhenti", foreground=MUTED)

    def cli_discover(self):
        from wfprint import discovery
        self.c_status.config(text="● mencari server...", foreground=MUTED)
        self.update_idletasks()
        box = self

        def work():
            try:
                found = discovery.discover(timeout=2.5)
            except Exception as e:
                found = []
                box.after(0, lambda: messagebox.showerror("wfprint", f"Discovery gagal: {e}"))
            box.after(0, lambda: box.show_found(found))

        threading.Thread(target=work, daemon=True).start()

    def show_found(self, found):
        self._found = [(ip, p, n) for ip, printers in found for p, n in sorted(printers.items())]
        self.c_found.delete(0, "end")
        for ip, p, n in self._found:
            self.c_found.insert("end", f"{ip} — 🖨 {n} (port {p})")
        self.c_status.config(
            text=f"● ketemu {len(self._found)} printer" if self._found else "● server tak ketemu",
            foreground=OK if self._found else FAIL)

    def cli_pick(self, _ev=None):
        sel = self.c_found.curselection()
        if not sel or not self._found:
            return
        ip, p, n = self._found[sel[0]]
        for e, v in ((self.c_host, ip), (self.c_port, p), (self.c_printer, n)):
            e.delete(0, "end")
            e.insert(0, v)
        if not self.c_driver.get().strip():
            self.c_driver.insert(0, n)

    def cli_probe(self):
        from wfprint import client
        host, port = self.c_host.get(), self.c_port.get()
        errs = validate_server(host, port, self.c_printer.get() or "x")
        if errs:
            messagebox.showerror("wfprint", "\n".join(errs))
            return
        ok = client.probe(host.strip(), int(port))
        self.c_status.config(text="● OK" if ok else "● FAIL — cek IP/port/firewall",
                             foreground=OK if ok else FAIL)

    def cli_setup(self):
        from wfprint import client
        vals = (self.c_host.get(), self.c_port.get(), self.c_printer.get(), self.c_driver.get())
        errs = validate_client(*vals)
        if errs:
            messagebox.showerror("wfprint", "\n".join(errs))
            return
        rc = client.setup(vals[0].strip(), int(vals[1]), vals[2].strip(), vals[3].strip())
        self.c_status.config(text="● printer terpasang" if rc == 0 else f"● setup gagal (rc={rc})",
                             foreground=OK if rc == 0 else FAIL)

    def cli_test(self):
        from wfprint import client
        name = self.c_printer.get().strip()
        if not name:
            messagebox.showerror("wfprint", "Nama printer wajib diisi.")
            return
        rc = client.print_test_page(name)
        self.c_status.config(text="● test page dikirim" if rc == 0 else f"● gagal (rc={rc})",
                             foreground=OK if rc == 0 else FAIL)


def run(start_minimized=False):
    App(start_minimized=start_minimized).mainloop()
