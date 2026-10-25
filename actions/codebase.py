"""Bounded local project indexing and source search."""
import ast
import json
from pathlib import Path
from core.storage import get_state,set_state

IGNORED={".git",".venv","venv","node_modules","__pycache__","dist","build"}
EXTENSIONS={".py",".js",".jsx",".ts",".tsx",".html",".css",".json",".md",".txt",".toml",".yml",".yaml"}
def _files(root):
    import os
    count=0
    for directory,dirs,files in os.walk(root):
        dirs[:]=[name for name in dirs if name not in IGNORED]
        for name in files:
            path=Path(directory)/name
            if path.suffix in EXTENSIONS and path.stat().st_size<=500000:
                yield path
                count+=1
                if count>=2000:
                    return

def codebase(parameters: dict, player=None):
    try:
        projects=get_state("code_projects",{})
        action=parameters.get("action","list")
        if action=="index":
            root=Path(parameters["path"]).expanduser().resolve()
            if not root.is_dir():
                raise ValueError("No existe esa carpeta.")
            name=parameters.get("name",root.name)
            paths=[str(p.relative_to(root)) for p in _files(root)]
            projects[name]={"root":str(root),"files":paths}
            set_state("code_projects",projects)
            return f"Proyecto {name} indexado: {len(paths)} archivos (límite 2000)."
        if action=="list":
            return json.dumps({k:{"root":v["root"],"files":len(v["files"])} for k,v in projects.items()},ensure_ascii=False)
        name=parameters.get("project",parameters.get("name",""))
        if name not in projects:
            raise ValueError("Proyecto no indexado. Usa index primero.")
        project=projects[name];root=Path(project["root"])
        if action=="remove":
            del projects[name];set_state("code_projects",projects)
            return "Índice eliminado; los archivos del proyecto se conservan."
        if action=="info":
            return json.dumps(project,ensure_ascii=False)[:15000]
        if action=="generate_docs":
            source=(root/parameters["file_path"]).resolve()
            if root not in source.parents or source.suffix!=".py":
                raise ValueError("Selecciona un archivo Python dentro del proyecto.")
            tree=ast.parse(source.read_text(encoding="utf-8"))
            return "\n".join(f"{type(n).__name__} {n.name} (línea {n.lineno}): {ast.get_docstring(n) or 'Sin documentación'}"
                             for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)))[:16000]
        if action not in {"search","find_symbol"}:
            raise ValueError("Acción no soportada.")
        query=str(parameters.get("query",parameters.get("symbol","")))
        if not query:
            raise ValueError("Indica query o symbol.")
        found=[]
        for source in _files(root):
            for line,text in enumerate(source.read_text(encoding="utf-8",errors="replace").splitlines(),1):
                if query.casefold() in text.casefold():
                    found.append({"file":str(source.relative_to(root)),"line":line,"text":text[:300]})
                    if len(found)>=50:
                        return json.dumps(found,ensure_ascii=False)
        return json.dumps(found,ensure_ascii=False)
    except Exception as exc:
        return f"Error de código: {exc}"
