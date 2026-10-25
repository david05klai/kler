"""Persistent preferences and actual action counters."""
import json
import threading
from core.storage import get_state,set_state
_lock = threading.RLock()

def _load_profile():
    return get_state("user_profile",{"name":"Señor","habits":{},"preferences":{},"notes":[]})
def _save_profile(profile):
    set_state("user_profile",profile)

def user_profile(parameters: dict, player=None):
    try:
        with _lock:
            profile = _load_profile()
            action = parameters.get("action","view")
            if action in {"get","view"}:
                return json.dumps(profile,ensure_ascii=False)
            if action in {"notes","habits"}:
                return json.dumps(profile.get(action,{}),ensure_ascii=False)
            if action=="set_name":
                if not parameters.get("name"):
                    raise ValueError("Falta el nombre.")
                profile["name"] = parameters["name"]
            elif action=="set_preference":
                if not parameters.get("key"):
                    raise ValueError("Falta la clave de preferencia.")
                profile.setdefault("preferences",{})[parameters["key"]] = parameters.get("value","")
            elif action=="add_note":
                if not parameters.get("note"):
                    raise ValueError("La nota está vacía.")
                profile.setdefault("notes",[]).append(parameters["note"])
            elif action=="reset":
                profile = {"name":"Señor","habits":{},"preferences":{},"notes":[]}
            else:
                raise ValueError("Acción de perfil desconocida.")
            _save_profile(profile)
            return "Perfil guardado."
    except Exception as exc:
        return f"Error de perfil: {exc}"

def record_action(name,args):
    with _lock:
        profile = _load_profile()
        habits = profile.setdefault("habits",{})
        habits[name] = habits.get(name,0)+1
        _save_profile(profile)
