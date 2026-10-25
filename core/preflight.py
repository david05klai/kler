"""Read-only installation checks; never prints credentials."""
import importlib.util
from pathlib import Path
from memory.config_manager import load_api_keys,is_configured

def inspect_installation():
    messages=[]
    cfg=load_api_keys()
    provider=cfg.get("ai_provider","gemini")
    messages.append("Proveedor: "+provider)
    messages.append("Configuración del proveedor lista." if is_configured() else "Falta configurar el proveedor en Ajustes.")
    model=Path(__file__).resolve().parent.parent/"config"/"vosk_model"
    messages.append("Modelo de voz local listo." if (model/"am"/"final.mdl").is_file() else "Falta el modelo de voz. Ejecuta download_vosk.py para activar por nombre.")
    for package,label in [("vosk","voz local"),("telegram","Telegram"),("winrt","notificaciones de Windows"),("yt_dlp","TikTok")]:
        try:
            installed=importlib.util.find_spec(package) is not None
        except (ImportError,ValueError):
            installed=False
        if not installed:
            messages.append(f"{label}: componente no instalado"+(" (opcional)." if package!="vosk" else "."))
    try:
        import sounddevice as sd
        from core.voice_input import device_id
        sd.check_input_settings(device=device_id(cfg.get("mic_device")),channels=1,dtype="int16",samplerate=16000)
        messages.append("Dispositivo de entrada compatible.")
    except Exception as exc:
        messages.append(f"Revisa el micrófono en Ajustes: {exc}")
    return messages
