"""Offline Windows speech, played through the selected sounddevice output."""
import base64
import logging
from pathlib import Path
import subprocess
import tempfile
import threading
import wave

log = logging.getLogger(__name__)


class SpeechOutput:
    def __init__(self):
        self.cancelled = threading.Event()
        self.process = None

    def stop(self):
        self.cancelled.set()
        process = self.process
        if process and process.poll() is None:
            process.terminate()

    def speak(self, text, device=None):
        import sounddevice as sd
        from core.voice_input import device_id
        self.cancelled.clear()
        encoded = base64.b64encode(str(text).encode("utf-8")).decode("ascii")
        with tempfile.TemporaryDirectory(prefix="kler-voice-") as temp:
            target = Path(temp) / "voice.wav"
            target64 = base64.b64encode(str(target).encode("utf-8")).decode("ascii")
            script = (
                "Add-Type -AssemblyName System.Speech;"
                "$voice=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "try {$voice.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,"
                "[System.Speech.Synthesis.VoiceAge]::NotSet,0,[System.Globalization.CultureInfo]::GetCultureInfo('es'))} catch {};"
                f"$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'));"
                f"$path=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{target64}'));"
                "$voice.SetOutputToWaveFile($path);$voice.Speak($text);$voice.Dispose();"
            )
            command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
            self.process = subprocess.Popen(["powershell","-NoProfile","-NonInteractive","-EncodedCommand",command],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                _, error = self.process.communicate(timeout=45)
                if self.cancelled.is_set():
                    return
                if self.process.returncode:
                    raise RuntimeError(error.decode(errors="replace")[:400])
                with wave.open(str(target), "rb") as wav:
                    if wav.getsampwidth() != 2:
                        raise ValueError("La voz de Windows devolvió un formato de audio no soportado.")
                    with sd.RawOutputStream(device=device_id(device), samplerate=wav.getframerate(),
                            channels=wav.getnchannels(), dtype="int16") as output:
                        while not self.cancelled.is_set():
                            data = wav.readframes(max(1, wav.getframerate() // 50))
                            if not data:
                                break
                            output.write(data)
            finally:
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    self.process.wait(timeout=3)
                self.process = None
