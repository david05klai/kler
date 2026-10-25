"""Validated, atomic configuration writes preserving optional integration settings."""
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading

_lock = threading.RLock()
def get_base_dir():
    return Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent
BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
def config_exists():
    return CONFIG_FILE.exists()
def is_configured():
    cfg = load_api_keys()
    provider = cfg.get("ai_provider","gemini")
    if provider == "ollama":
        return bool(cfg.get("ollama_model"))
    key = cfg.get("openrouter_api_key" if provider == "openrouter" else "gemini_api_key")
    return bool(key) and not str(key).startswith("YOUR_")
def load_api_keys():
    with _lock:
        if not CONFIG_FILE.exists():
            return {}
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("La configuración debe ser un objeto JSON.")
            return data
        except (OSError, ValueError):
            logging.exception("No se pudo leer la configuración")
            return {}
def save_api_keys(keys):
    if not isinstance(keys, dict):
        raise ValueError("La configuración debe ser un diccionario.")
    with _lock:
        ensure_config_dir()
        if CONFIG_FILE.exists():
            # Refuse to overwrite a corrupt file silently.
            current = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(current, dict):
                raise ValueError("La configuración existente no es válida.")
        else:
            current = {}
        current.update(keys)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=CONFIG_DIR,suffix=".tmp",delete=False) as stream:
                temp_name = stream.name
                json.dump(current, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, CONFIG_FILE)
        finally:
            if temp_name and Path(temp_name).exists():
                Path(temp_name).unlink()
def get_gemini_key():
    value = load_api_keys().get("gemini_api_key","")
    return value[0] if isinstance(value,list) and value else value
