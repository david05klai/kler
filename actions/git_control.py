"""Git commands with argument arrays, real exit codes and bounded execution."""
from pathlib import Path
import subprocess

def git_control(parameters: dict, player=None):
    try:
        root = Path(parameters["repo_path"]).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("No existe el repositorio.")
        action = parameters.get("action","status")
        count = str(min(50,max(1,int(parameters.get("n",10)))))
        remote = str(parameters.get("remote","origin"))
        branch = str(parameters.get("branch_name",""))
        if remote.startswith("-") or branch.startswith("-"):
            raise ValueError("Nombre de rama o remoto inválido.")
        commands = {"status":["status","--short","--branch"],"log":["log","--oneline","-"+count],
            "branches":["branch","--list"],"pull":["pull","--ff-only",remote],"push":["push",remote],
            "branch_create":["branch",branch],"checkout":["switch",branch],"analyze":["status","--porcelain=v1"]}
        if action=="diff":
            args = ["diff"] + (["--cached"] if parameters.get("staged") else [])
            if parameters.get("file"):
                args += ["--",str(parameters["file"])]
        elif action=="add":
            files = parameters.get("files") or ["."]
            if not isinstance(files,list):
                raise ValueError("files debe ser una lista.")
            args = ["add","--"] + [str(f) for f in files]
        elif action=="commit":
            if not str(parameters.get("message","")).strip():
                raise ValueError("Falta el mensaje del commit.")
            if parameters.get("add_all",True):
                staged = subprocess.run(["git","-C",str(root),"add","--all"],capture_output=True,text=True,timeout=20)
                if staged.returncode:
                    return "Error de Git: " + staged.stderr
            args = ["commit","-m",parameters["message"]]
        elif action=="stash":
            sub = parameters.get("sub","list")
            if sub not in {"push","pop","list"}:
                raise ValueError("Subcomando stash no soportado.")
            args = ["stash",sub]
        elif action in commands:
            args = commands[action]
            if action in {"branch_create","checkout"} and not branch:
                raise ValueError("Falta branch_name.")
        else:
            raise ValueError("Acción Git no soportada.")
        result = subprocess.run(["git","-C",str(root)]+args,capture_output=True,text=True,encoding="utf-8",
            errors="replace",timeout=45,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        output = (result.stdout+"\n"+result.stderr).strip()
        return (output or "Git completó la operación sin salida.")[:16000] if result.returncode==0 else f"Error de Git ({result.returncode}): {output[:8000]}"
    except Exception as exc:
        return f"Error de Git: {exc}"
