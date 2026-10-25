"""Analyze metadata actually returned by yt-dlp, without fabricating unavailable metrics."""
import json
from urllib.parse import urlparse

def tiktok_analyzer(parameters: dict, player=None):
    try:
        import yt_dlp
        url=str(parameters.get("profile_url",""))
        parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.hostname not in {"www.tiktok.com","tiktok.com"}:
            raise ValueError("Indica una URL HTTPS de TikTok.")
        count=min(20,max(1,int(parameters.get("max_videos",8))))
        with yt_dlp.YoutubeDL({"quiet":True,"skip_download":True,"extract_flat":True,"playlistend":count,
                              "socket_timeout":15,"retries":1,"extractor_retries":1}) as downloader:
            info=downloader.extract_info(url,download=False)
            if not info:
                raise ValueError("TikTok no devolvió metadatos públicos.")
            entries=list(info.get("entries",[]))[:count] if "entries" in info else [info]
        videos=[{k:e.get(k) for k in ["id","title","url","view_count","like_count","comment_count"]} for e in entries if e]
        return json.dumps({"videos":videos,"note":"Los valores null no estaban disponibles públicamente."},ensure_ascii=False)
    except ImportError:
        return "Error: instala requirements-optional.txt para habilitar el análisis público de TikTok."
    except Exception as exc:
        return f"Error al consultar TikTok: {exc}"
