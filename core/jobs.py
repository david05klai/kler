"""Persistent jobs with two workers and atomic claims; survives application restarts."""
import json
import logging
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from core.storage import connection

log = logging.getLogger(__name__)
_runner = None
_lock = threading.Lock()


def local_now():
    from memory.config_manager import load_api_keys
    from zoneinfo import ZoneInfo
    try:
        return datetime.now(ZoneInfo(load_api_keys().get('timezone', 'America/Bogota')))
    except Exception:
        return datetime.now().astimezone()


def parse_datetime(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        result = datetime.strptime(str(value), '%d/%m/%Y %H:%M')
    return result if result.tzinfo else result.replace(tzinfo=local_now().tzinfo)


def create_job(name, due, action, parameters, frequency='once', interval_seconds=0):
    if not name.strip() or action not in {'notify', 'backup', 'file_controller', 'browser_control', 'custom_script'}:
        raise ValueError('Nombre o acción de tarea inválidos.')
    if frequency not in {'once', 'daily', 'weekly', 'interval'}:
        raise ValueError('Frecuencia inválida.')
    if frequency == 'interval' and interval_seconds < 60:
        raise ValueError('El intervalo mínimo es un minuto.')
    job_id = uuid.uuid4().hex[:12]
    with connection() as db:
        db.execute('INSERT INTO jobs(id,name,due,frequency,interval_seconds,action,parameters) VALUES(?,?,?,?,?,?,?)',
                   (job_id, name, due, frequency, interval_seconds, action, json.dumps(parameters, ensure_ascii=False)))
    return job_id


def list_jobs():
    with connection() as db:
        return [dict(row) for row in db.execute('SELECT * FROM jobs ORDER BY due')]


def change_job(prefix, action):
    matches = [job for job in list_jobs() if job['id'].startswith(prefix) or job['name'] == prefix]
    if not prefix or len(matches) != 1:
        raise ValueError('Indica un ID o nombre de tarea único; consulta la lista primero.')
    if matches[0]["status"] == "running" and action != "disable":
        raise RuntimeError("La tarea se está ejecutando; espera a que termine.")
    job_id = matches[0]['id']
    with connection() as db:
        if action == 'delete':
            db.execute('DELETE FROM jobs WHERE id=?', (job_id,))
        elif action in {'enable', 'disable'}:
            db.execute("UPDATE jobs SET enabled=?,status='pending' WHERE id=?", (int(action == 'enable'), job_id))
        elif action == 'run_now':
            db.execute("UPDATE jobs SET due=?,enabled=1,status='pending' WHERE id=?", (time.time(), job_id))
        else:
            raise ValueError('Acción desconocida.')
    return job_id


def execute_action(action, parameters, player=None, speak=None):
    if action == 'notify':
        message = str(parameters.get('message', parameters.get('text', 'Recordatorio de Kler')))
        if player:
            player.write_log('⏰ ' + message)
        voice = speak or getattr(player, 'speak', None)
        if callable(voice):
            voice(message)
        return message
    if action == 'backup':
        source = Path(parameters['source']).expanduser().resolve()
        destination = Path(parameters['destination']).expanduser().resolve()
        if destination == source or source in destination.parents:
            raise ValueError('La copia debe guardarse fuera de la carpeta de origen.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        return f'Copia guardada en {destination}'
    if action == 'custom_script':
        from actions.terminal_agent import terminal_agent as handler
    elif action == 'file_controller':
        from actions.file_controller import file_controller as handler
    elif action == 'browser_control':
        from actions.browser_control import browser_control as handler
    else:
        raise ValueError('Acción no soportada: ' + action)
    result = str(handler(parameters, player=player))
    if result.lower().startswith(('error', 'excepción', 'fallo', '⚠')):
        raise RuntimeError(result)
    return result


class JobRunner:
    def __init__(self, player=None, speak=None):
        self.player, self.speak = player, speak
        self.stop_event = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='kler-job')
        self.slots = threading.BoundedSemaphore(2)
        self.thread = threading.Thread(target=self._loop, name='kler-scheduler', daemon=True)

    def start(self):
        with connection() as db:
            db.execute("UPDATE jobs SET status='failed',last_error='Kler se cerró durante la ejecución; revisa antes de reintentar.' WHERE status='running'")
        self.thread.start()

    def tick(self, now=None):
        now = time.time() if now is None else now
        with connection() as db:
            due_jobs = [dict(row) for row in db.execute("SELECT * FROM jobs WHERE enabled=1 AND status='pending' AND due<=? ORDER BY due LIMIT 2", (now,))]
        for job in due_jobs:
            if not self.slots.acquire(blocking=False):
                break
            with connection() as db:
                claimed = db.execute("UPDATE jobs SET status='running' WHERE id=? AND status='pending'", (job['id'],)).rowcount == 1
            if claimed:
                self.pool.submit(self._execute, job)
            else:
                self.slots.release()

    def _execute(self, job):
        try:
            result = execute_action(job['action'], json.loads(job['parameters']), self.player, self.speak)
            now, due, frequency = time.time(), job['due'], job['frequency']
            if frequency in {'daily', 'weekly'}:
                next_time = datetime.fromtimestamp(due, local_now().tzinfo)
                while next_time.timestamp() <= now:
                    next_time += timedelta(days=1 if frequency == 'daily' else 7)
                due = next_time.timestamp()
            elif frequency == 'interval':
                step = job['interval_seconds']
                due += (int(max(0, now - due) // step) + 1) * step
            with connection() as db:
                db.execute('UPDATE jobs SET status=?,due=?,last_run=?,last_error=NULL WHERE id=?',
                           ('done' if frequency == 'once' else 'pending', due, now, job['id']))
            if self.player and job['action'] != 'notify':
                self.player.write_log(f"Tarea {job['name']}: {result}")
        except Exception as exc:
            log.exception('Job %s failed', job['id'])
            with connection() as db:
                db.execute("UPDATE jobs SET status='failed',last_error=?,last_run=? WHERE id=?", (str(exc), time.time(), job['id']))
            if self.player:
                self.player.write_log(f"Error en tarea {job['name']}: {exc}")
        finally:
            self.slots.release()

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception:
                log.exception('Scheduler tick failed')
            self.stop_event.wait(0.5)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.pool.shutdown(wait=False, cancel_futures=True)


def start_runner(player=None, speak=None):
    global _runner
    with _lock:
        if _runner is None or _runner.stop_event.is_set():
            _runner = JobRunner(player, speak)
            _runner.start()
        else:
            _runner.player, _runner.speak = player, speak
    return _runner


def stop_runner():
    if _runner:
        _runner.stop()
