"""Bounded priority queue for background research."""
import logging
import os
import queue
import threading
import uuid
from pathlib import Path
from datetime import datetime

class TaskPriority:
    LOW = 1
    NORMAL = 2
    HIGH = 3

class TaskQueue:
    def __init__(self, workers=2, max_pending=8):
        self.queue = queue.PriorityQueue(maxsize=max_pending)
        self._stop = threading.Event()
        self._workers = []
        self._count = 0
        self._lock = threading.Lock()
        for i in range(workers):
            thread = threading.Thread(target=self._work, name=f"kler-research-{i}", daemon=True)
            thread.start()
            self._workers.append(thread)

    def submit(self, goal, priority=TaskPriority.NORMAL, speak=None):
        task_id = uuid.uuid4().hex[:8]
        with self._lock:
            self._count += 1
            sequence = self._count
        try:
            self.queue.put_nowait((-priority, sequence, goal, task_id, speak))
        except queue.Full:
            return "Error: hay demasiadas tareas pendientes. Espera a que termine una."
        if speak:
            speak("Tarea encolada. Te avisaré cuando termine.")
        return task_id

    def _work(self):
        while not self._stop.is_set():
            try:
                _, _, goal, task_id, speak = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._process_task(goal, task_id, speak)
            finally:
                self.queue.task_done()

    def _process_task(self, goal, task_id, speak):
        from actions.openrouter_agent import openrouter_agent
        try:
            result = openrouter_agent(str(goal))
            if str(result).lower().startswith(("error", "no se encontró", "no se pudo")):
                raise RuntimeError(result)
            desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)
            target = desktop / f"Reporte_Kler_{datetime.now():%Y%m%d_%H%M%S}_{task_id}.md"
            target.write_text(str(result), encoding="utf-8")
            if speak:
                speak(f"Reporte terminado y guardado en {target.name}.")
        except Exception:
            logging.exception("Research task %s failed", task_id)
            if speak:
                speak("La tarea falló. Revisa el historial para ver el error.")

    def shutdown(self):
        self._stop.set()

_instance = None
_instance_lock = threading.Lock()
def get_queue():
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = TaskQueue()
    return _instance
