"""Install the Spanish Vosk model without replacing a working model."""
from pathlib import Path
import tempfile
import urllib.request
import zipfile

URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
BASE=Path(__file__).resolve().parent

def install_model(base=BASE):
    config=Path(base)/"config"
    config.mkdir(parents=True,exist_ok=True)
    target=config/"vosk_model"
    if (target/"am"/"final.mdl").is_file():
        print("Modelo Vosk ya instalado.")
        return target
    if target.exists():
        raise ValueError(f"Hay un modelo incompleto en {target}. Muévelo antes de reinstalar.")
    with tempfile.TemporaryDirectory(prefix="vosk-install-",dir=config) as temp:
        staging=Path(temp).resolve()
        archive=staging/"model.zip"
        print("Descargando el modelo de voz local…")
        with urllib.request.urlopen(URL,timeout=30) as response,archive.open("wb") as out:
            size=0
            while True:
                chunk=response.read(1024*1024)
                if not chunk:
                    break
                size+=len(chunk)
                if size>80_000_000:
                    raise ValueError("La descarga superó el tamaño esperado.")
                out.write(chunk)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                path=(staging/member.filename).resolve()
                if staging not in path.parents:
                    raise ValueError("El archivo contiene una ruta inválida.")
            if sum(member.file_size for member in z.infolist())>250_000_000:
                raise ValueError("El modelo descomprimido supera el límite.")
            z.extractall(staging)
        extracted=staging/"vosk-model-small-es-0.42"
        if not (extracted/"am"/"final.mdl").is_file():
            raise ValueError("El modelo descargado está incompleto.")
        extracted.rename(target)
    print("Modelo local listo:",target)
    return target

if __name__=="__main__":
    install_model()
