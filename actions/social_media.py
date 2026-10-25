"""Prepare reviewable drafts; opening a composer is not reported as publication."""
from pathlib import Path
from urllib.parse import urlencode,quote
import uuid
import webbrowser

def social_media(parameters: dict, player=None):
    platform=parameters.get("platform","").lower()
    action=parameters.get("action","").lower()
    text=str(parameters.get("text",parameters.get("content",""))).strip()
    homes={"twitter":"https://x.com","instagram":"https://www.instagram.com","tiktok":"https://www.tiktok.com","linkedin":"https://www.linkedin.com"}
    if platform not in homes:
        return "Error: plataforma no soportada."
    if action in {"profile","perfil","feed","timeline","trending"}:
        username=str(parameters.get("username","")).lstrip("@")
        url=homes[platform]
        if username and action in {"profile","perfil"}:
            url += ("/@" if platform=="tiktok" else "/in/" if platform=="linkedin" else "/")+quote(username,safe="")
        return f"Página abierta: {url}" if webbrowser.open(url) else "Error: no se pudo abrir el navegador."
    if action not in {"draft","post","tweet","publicar"}:
        return "Error: esta integración prepara borradores y abre perfiles; no realiza esa operación en la cuenta."
    if not text:
        return "Error: el contenido está vacío."
    folder=Path.home()/"Documents"/"Kler"/"Borradores";folder.mkdir(parents=True,exist_ok=True)
    target=folder/f"{platform}_{uuid.uuid4().hex[:10]}.txt";target.write_text(text,encoding="utf-8")
    if platform=="twitter":
        webbrowser.open("https://x.com/intent/tweet?"+urlencode({"text":text}))
    else:
        webbrowser.open(homes[platform])
    return f"Borrador guardado en {target}. La publicación está pendiente de que lo revises y envíes en {platform}."
