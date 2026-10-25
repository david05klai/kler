"""Actual desktop listing, statistics, organization and wallpaper changes."""
import ctypes
from pathlib import Path
import uuid
import requests

def desktop_control(parameters: dict, player=None):
    try:
        from actions.file_controller import file_controller,resolve_path
        action=parameters.get("action","list")
        root=Path(resolve_path(parameters.get("search_path","desktop")))
        if action in {"list","stats"}:
            items=list(root.iterdir())
            if action=="stats":
                files=[p for p in items if p.is_file()]
                return f"{len(files)} archivos, {len(items)-len(files)} carpetas, {sum(p.stat().st_size for p in files)} bytes."
            return "\n".join(p.name+("/" if p.is_dir() else "") for p in items[:200])
        if action=="organize":
            moved=0
            for source in root.iterdir():
                if not source.is_file() or source.suffix.lower() in {".ini",".lnk"}:
                    continue
                folder=root/("Archivos_"+(source.suffix[1:].lower() or "sin_extension"))
                folder.mkdir(exist_ok=True)
                destination=folder/source.name
                if not destination.exists():
                    source.rename(destination);moved+=1
            return f"Se organizaron {moved} archivos por extensión en {root}."
        if action in {"wallpaper","wallpaper_url"}:
            path=Path(parameters.get("path","")).expanduser()
            if action=="wallpaper_url":
                url=str(parameters.get("url",""))
                if not url.startswith("https://"):
                    raise ValueError("Usa una URL HTTPS de imagen.")
                directory=Path.home()/"Pictures"/"Kler";directory.mkdir(parents=True,exist_ok=True)
                path=directory/f"wallpaper_{uuid.uuid4().hex[:10]}.png"
                from PIL import Image
                import io
                with requests.get(url,stream=True,timeout=(5,15)) as response:
                    response.raise_for_status()
                    data=bytearray()
                    for chunk in response.iter_content(65536):
                        data.extend(chunk)
                        if len(data)>12_000_000:
                            raise ValueError("La imagen supera 12 MB.")
                Image.open(io.BytesIO(data)).save(path)
            if not path.is_file():
                raise ValueError("No existe la imagen.")
            if not ctypes.windll.user32.SystemParametersInfoW(20,0,str(path.resolve()),3):
                raise OSError("Windows no aceptó el fondo de pantalla.")
            return f"Fondo aplicado: {path}"
        if action=="task" and parameters.get("search_name"):
            return file_controller({"action":"find","path":str(root),"name":parameters["search_name"]},player=player)
        raise ValueError("Acción soportada: list, stats, organize, wallpaper o wallpaper_url.")
    except Exception as exc:
        return f"Error de escritorio: {exc}"
