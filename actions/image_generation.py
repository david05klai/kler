"""Generate actual image files through the configured Gemini image model."""
import base64
import io
import json
from pathlib import Path
import uuid

def image_generation(parameters: dict, player=None):
    saved = []
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from memory.config_manager import load_api_keys,get_gemini_key
        cfg = load_api_keys()
        key = get_gemini_key()
        if not key or str(key).startswith("YOUR_"):
            raise ValueError("Falta una clave válida de Gemini.")
        prompt = str(parameters.get("prompt","")).strip()
        if not prompt:
            raise ValueError("La descripción está vacía.")
        directory = Path(parameters.get("save_path",str(Path.home()/"Pictures"/"Kler"))).expanduser()
        directory.mkdir(parents=True,exist_ok=True)
        client = genai.Client(api_key=key,http_options={"timeout":60000})
        try:
            for _ in range(min(4,max(1,int(parameters.get("count",1))))):
                response = client.models.generate_content(
                    model=cfg.get("image_model","gemini-2.5-flash-image"),contents=prompt,
                    config=types.GenerateContentConfig(response_modalities=["TEXT","IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio=parameters.get("aspect_ratio","1:1"))))
                for part in response.parts or []:
                    if part.inline_data and str(part.inline_data.mime_type).startswith("image/"):
                        image = Image.open(io.BytesIO(part.inline_data.data))
                        target = directory/f"kler_{uuid.uuid4().hex[:12]}.png"
                        image.save(target)
                        saved.append(str(target.resolve()))
        finally:
            client.close()
        if not saved:
            raise RuntimeError("El proveedor no devolvió ninguna imagen; revisa el modelo o el motivo de bloqueo.")
        if player and getattr(player,"_win",None):
            data = base64.b64encode(Path(saved[0]).read_bytes()).decode()
            player._win._holo_sig.emit("",f'<img style="max-width:100%;height:auto" src="data:image/png;base64,{data}">')
        return json.dumps({"saved_images":saved},ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error":str(exc),"saved_images":saved},ensure_ascii=False)
