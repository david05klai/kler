"""Paths for Windows libraries that still use ANSI filesystem APIs."""
import os
from pathlib import Path


def native_model_path(path):
    path = Path(path).resolve()
    if os.name != "nt" or str(path).isascii():
        return str(path)
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    if length and length < len(buffer) and buffer.value.isascii():
        return buffer.value
    # Vosk also works with an ASCII relative path when the project folder has accents.
    try:
        relative = str(path.relative_to(Path.cwd().resolve()))
        if relative.isascii():
            return relative
    except ValueError:
        pass
    raise ValueError("Vosk no puede abrir esta ruta de Windows. Mueve el modelo a una ruta sin acentos o habilita nombres cortos.")
