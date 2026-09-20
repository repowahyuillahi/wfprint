import ctypes
from ctypes import wintypes


class SpoolError(Exception):
    pass


class Spool:
    def open(self, printer_name: str) -> int:
        raise NotImplementedError

    def start_doc(self, handle: int, doc_name: str) -> int:
        raise NotImplementedError

    def write(self, handle: int, data: bytes) -> int:
        raise NotImplementedError

    def end_doc(self, handle: int) -> None:
        raise NotImplementedError

    def close(self, handle: int) -> None:
        raise NotImplementedError

    def abort(self, handle: int) -> None:
        self.close(handle)

    def list_printers(self) -> list:
        raise NotImplementedError


class FakeSpool(Spool):
    def __init__(self, names=None):
        self.jobs: dict = {}
        self._open: set = set()
        self._names = list(names) if names else []

    def list_printers(self) -> list:
        return list(self._names)

    def open(self, printer_name: str) -> int:
        h = abs(hash(printer_name)) % 100000 + 1
        self._open.add(h)
        self.jobs[h] = b""
        return h

    def start_doc(self, handle: int, doc_name: str) -> int:
        if handle not in self._open:
            raise SpoolError("bad handle")
        return 1

    def write(self, handle: int, data: bytes) -> int:
        if handle not in self._open:
            raise SpoolError("bad handle")
        self.jobs[handle] += bytes(data)
        return len(data)

    def end_doc(self, handle: int) -> None:
        if handle not in self._open:
            raise SpoolError("bad handle")

    def close(self, handle: int) -> None:
        self._open.discard(handle)


class _DOCINFO(ctypes.Structure):
    _fields_ = [("pDocName", wintypes.LPWSTR),
                ("pOutputFile", wintypes.LPWSTR),
                ("pDatatype", wintypes.LPWSTR)]


class _PRINTER_INFO_4(ctypes.Structure):
    _fields_ = [("pPrinterName", wintypes.LPWSTR),
                ("pServerName", wintypes.LPWSTR),
                ("Attributes", wintypes.DWORD)]


class WinSpool(Spool):
    def __init__(self):
        self._dll = ctypes.WinDLL("winspool.drv")
        self._dll.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
        self._dll.OpenPrinterW.restype = wintypes.BOOL
        self._dll.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(_DOCINFO)]
        self._dll.StartDocPrinterW.restype = wintypes.DWORD
        self._dll.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self._dll.WritePrinter.restype = wintypes.BOOL
        self._dll.EndDocPrinter.argtypes = [wintypes.HANDLE]
        self._dll.EndDocPrinter.restype = wintypes.BOOL
        self._dll.AbortPrinter.argtypes = [wintypes.HANDLE]
        self._dll.AbortPrinter.restype = wintypes.BOOL
        self._dll.ClosePrinter.argtypes = [wintypes.HANDLE]
        self._dll.ClosePrinter.restype = wintypes.BOOL
        self._dll.EnumPrintersW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD,
                                            ctypes.c_void_p, wintypes.DWORD,
                                            ctypes.POINTER(wintypes.DWORD),
                                            ctypes.POINTER(wintypes.DWORD)]
        self._dll.EnumPrintersW.restype = wintypes.BOOL

    def list_printers(self) -> list:
        flags = 0x00000002 | 0x00000004
        needed = wintypes.DWORD(0)
        returned = wintypes.DWORD(0)
        self._dll.EnumPrintersW(flags, None, 4, None, 0, ctypes.byref(needed), ctypes.byref(returned))
        if needed.value == 0:
            return []
        buf = ctypes.create_string_buffer(needed.value)
        if not self._dll.EnumPrintersW(flags, None, 4, buf, needed.value,
                                       ctypes.byref(needed), ctypes.byref(returned)):
            raise SpoolError("EnumPrinters gagal")
        out = []
        addr = ctypes.addressof(buf)
        size = ctypes.sizeof(_PRINTER_INFO_4)
        for i in range(int(returned.value)):
            info = _PRINTER_INFO_4.from_address(addr + i * size)
            if info.pPrinterName:
                out.append(info.pPrinterName)
        return out

    def open(self, printer_name: str) -> int:
        h = wintypes.HANDLE()
        if not self._dll.OpenPrinterW(printer_name, ctypes.byref(h), None):
            raise SpoolError(f"printer offline: {printer_name}")
        return int(h.value)

    def start_doc(self, handle: int, doc_name: str) -> int:
        info = _DOCINFO(pDocName=doc_name, pOutputFile=None, pDatatype="RAW")
        jid = self._dll.StartDocPrinterW(wintypes.HANDLE(handle), 1, ctypes.byref(info))
        if jid == 0:
            raise SpoolError("StartDocPrinter gagal")
        return int(jid)

    def write(self, handle: int, data: bytes) -> int:
        written = wintypes.DWORD(0)
        buf = ctypes.create_string_buffer(bytes(data))
        if not self._dll.WritePrinter(wintypes.HANDLE(handle), buf, len(data), ctypes.byref(written)):
            raise SpoolError(f"WritePrinter gagal setelah {int(written.value)} byte")
        return int(written.value)

    def end_doc(self, handle: int) -> None:
        self._dll.EndDocPrinter(wintypes.HANDLE(handle))

    def abort(self, handle: int) -> None:
        self._dll.AbortPrinter(wintypes.HANDLE(handle))

    def close(self, handle: int) -> None:
        self._dll.ClosePrinter(wintypes.HANDLE(handle))
