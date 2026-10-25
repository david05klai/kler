"""Persistent searchable notes, snippets and references."""
import json
import threading
import uuid
from pathlib import Path
from core.storage import get_state,set_state

_lock = threading.RLock()
def knowledge_base(parameters: dict, player=None):
    try:
        with _lock:
            entries = get_state("knowledge",[])
            action = parameters.get("action","list")
            if action in {"add","save","store"}:
                if not parameters.get("title") or not parameters.get("content"):
                    raise ValueError("Indica título y contenido.")
                entry = {k:parameters.get(k,"") for k in ["title","content","type","tags"]}
                entry["id"] = uuid.uuid4().hex[:12]
                entries.append(entry)
                set_state("knowledge",entries)
                return "Entrada guardada: "+entry["id"]
            if action in {"search","find"}:
                query = str(parameters.get("query","")).casefold()
                matches = [e for e in entries if query in json.dumps(e,ensure_ascii=False).casefold()]
                return json.dumps(matches[:20],ensure_ascii=False)[:20000]
            if action=="list":
                return json.dumps([{k:e[k] for k in ["id","title","tags"]} for e in entries],ensure_ascii=False)[:15000]
            if action=="stats":
                return f"Entradas guardadas: {len(entries)}"
            if action=="export":
                path = Path(parameters.get("path",str(Path.home()/"Documents"/"Kler_conocimiento.json"))).expanduser()
                if path.exists():
                    raise ValueError("Ya existe el archivo de destino.")
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding="utf-8")
                return f"Base exportada en {path}"
            matches = [e for e in entries if e["id"]==parameters.get("entry_id")]
            if len(matches)!=1:
                raise ValueError("No existe esa entrada; consulta list.")
            entry = matches[0]
            if action in {"get","read","view"}:
                return json.dumps(entry,ensure_ascii=False)[:20000]
            if action=="update":
                entry.update({k:parameters[k] for k in ["title","content","type","tags"] if k in parameters})
            elif action=="delete":
                entries.remove(entry)
            else:
                raise ValueError("Acción no soportada.")
            set_state("knowledge",entries)
            return f"Entrada {entry['id']}: {action} completado."
    except Exception as exc:
        return f"Error de conocimiento: {exc}"
