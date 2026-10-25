"""Rotating logs and real timing measurements, initialized before optional imports."""
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
from pathlib import Path

_lock = threading.Lock()
_values = {}
def record(name, seconds):
    with _lock:
        _values.setdefault(name, deque(maxlen=100)).append(float(seconds))

def snapshot():
    with _lock:
        return {name: {"last_ms":round(v[-1]*1000,1),"mean_ms":round(sum(v)/len(v)*1000,1),"samples":len(v)}
                for name,v in _values.items() if v}

def setup():
    root = logging.getLogger()
    if getattr(root, "_kler_setup", False):
        return
    path = Path(__file__).resolve().parent.parent / "kler.log"
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root._kler_setup = True

class ConsoleLog:
    def __init__(self, original, level):
        self.original, self.level = original, level
        self._local = threading.local()
    def write(self, data):
        if self.original:
            try:
                self.original.write(data)
            except (UnicodeError, OSError):
                pass
        buffer = getattr(self._local, "buffer", "") + data
        while "\n" in buffer:
            line, buffer = buffer.split("\n",1)
            if line.strip():
                logging.getLogger("kler.console").log(self.level, line.rstrip())
        self._local.buffer = buffer
        return len(data)
    def flush(self):
        if self.original:
            self.original.flush()
    @property
    def encoding(self):
        return "utf-8"

def redirect_console():
    import sys
    if not isinstance(sys.stdout, ConsoleLog):
        sys.stdout = ConsoleLog(sys.stdout, logging.INFO)
        sys.stderr = ConsoleLog(sys.stderr, logging.ERROR)
