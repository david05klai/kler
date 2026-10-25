"""Bound both running and pending tool calls; cancelling a Future does not free its slot early."""
from concurrent.futures import ThreadPoolExecutor
import threading

class BoundedExecutor(ThreadPoolExecutor):
    def __init__(self, max_workers=2, max_pending=4, **kwargs):
        super().__init__(max_workers=max_workers, **kwargs)
        self._slots = threading.BoundedSemaphore(max_pending)

    def submit(self, fn, /, *args, **kwargs):
        if not self._slots.acquire(blocking=False):
            raise RuntimeError("Hay demasiadas herramientas ejecutándose. Espera a que terminen.")
        try:
            future = super().submit(fn, *args, **kwargs)
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(lambda _: self._slots.release())
        return future
