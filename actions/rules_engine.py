"""Persistent phrase rules with real bounded action dispatch."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from core.storage import get_state, set_state
from core.jobs import execute_action

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kler-rule")
_slots = threading.BoundedSemaphore(4)
_lock = threading.RLock()
_player = None
_speak = None


def _load_rules():
    rules = get_state("phrase_rules")
    if rules is None:
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "config" / "rules.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rules = data.get("rules", []) if isinstance(data, dict) else data
            rules = [r for r in rules if isinstance(r, dict) and r.get("phrase") and isinstance(r.get("action"), dict)]
        except (OSError, ValueError):
            rules = []
        set_state("phrase_rules", rules)
    return rules


def rules_engine(parameters: dict, player=None) -> str:
    try:
        with _lock:
            rules = _load_rules()
            action = parameters.get("action", "list")
            name = str(parameters.get("name", "")).strip()
            if action == "list":
                return json.dumps(rules, ensure_ascii=False)
            if not name:
                raise ValueError("Indica el nombre de la regla.")
            if action == "trigger":
                matches = [r for r in rules if r.get("name")==name]
                if not matches:
                    raise ValueError("No existe esa regla.")
                _run_action(matches[0]["action"])
                return "Regla enviada a ejecución; consulta el historial para ver el resultado."
            if action in {"create", "add", "add_rule"}:
                phrase = str(parameters.get("phrase", "")).strip()
                task = parameters.get("task_action", parameters.get("rule_action", {}))
                if not phrase or not isinstance(task, dict) or not task.get("type"):
                    raise ValueError("Indica phrase y task_action con type y parameters.")
                rules = [r for r in rules if r.get("name") != name]
                rules.append({"name":name,"phrase":phrase,"action":task,"enabled":True})
            elif action in {"delete", "remove"}:
                rules = [r for r in rules if r.get("name") != name]
            elif action in {"enable", "disable"}:
                found = False
                for rule in rules:
                    if rule.get("name") == name:
                        rule["enabled"] = action == "enable"
                        found = True
                if not found:
                    raise ValueError("No existe esa regla.")
            else:
                raise ValueError("Acción no soportada.")
            set_state("phrase_rules", rules)
        return f"Regla {name}: {action} guardado."
    except Exception as exc:
        return f"Error de reglas: {exc}"


def start_rules_runner(player=None, speak=None):
    global _player, _speak
    _player, _speak = player, speak


def check_phrase_triggers(text):
    return [r for r in _load_rules() if r.get("enabled", True) and r.get("phrase", "").casefold() in text.casefold()]


def _run_action(action):
    if not isinstance(action, dict) or not action.get("type"):
        raise ValueError("La regla requiere una acción con type y parameters.")
    if not _slots.acquire(blocking=False):
        raise RuntimeError("La cola de reglas está llena.")
    def run():
        try:
            result = execute_action(action["type"], action.get("parameters", {}), _player, _speak)
            if _player:
                _player.write_log(f"Regla ejecutada: {result}")
        except Exception as exc:
            if _player:
                _player.write_log(f"Error al ejecutar regla: {exc}")
        finally:
            _slots.release()
    return _pool.submit(run)
