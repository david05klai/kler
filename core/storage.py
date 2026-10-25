"""Transactional local state shared by UI, reminders and automations."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get('KLER_DB_PATH', str(BASE_DIR / 'config' / 'kler.sqlite3')))


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, due REAL NOT NULL,
            frequency TEXT NOT NULL, interval_seconds REAL NOT NULL DEFAULT 0,
            action TEXT NOT NULL, parameters TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending', last_error TEXT, last_run REAL)''')
        db.execute("CREATE INDEX IF NOT EXISTS jobs_due ON jobs(enabled,status,due)")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def get_state(key, default=None):
    with connection() as db:
        row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default


def set_state(key, value):
    with connection() as db:
        db.execute('INSERT INTO state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   (key, json.dumps(value, ensure_ascii=False)))
