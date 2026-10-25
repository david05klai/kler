"""Optional offline acoustic smoke test. Synthesizes files; never records or plays audio."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from test_runtime import FakeOwner
from core.voice_input import VoiceInput
from core.paths import native_model_path

MODEL=Path(__file__).resolve().parent.parent/"config"/"vosk_model"

@unittest.skipUnless((MODEL/"am"/"final.mdl").is_file(),"Install the Spanish Vosk model to run acoustic checks")
class AcousticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import vosk
        vosk.SetLogLevel(-1)
        cls.model=vosk.Model(native_model_path(MODEL))

    def recognize(self, text):
        import vosk
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"speech.wav"
            text64=base64.b64encode(text.encode()).decode()
            path64=base64.b64encode(str(path).encode()).decode()
            script=(
                "Add-Type -AssemblyName System.Speech;$v=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "try{$v.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,"
                "[System.Speech.Synthesis.VoiceAge]::NotSet,0,[Globalization.CultureInfo]::GetCultureInfo('es'))}catch{};"
                f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path64}'));"
                f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text64}'));"
                "$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,"
                "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono);"
                "$v.SetOutputToWaveFile($p,$f);$v.Speak($t);$v.Dispose();")
            subprocess.run(["powershell","-NoProfile","-NonInteractive","-EncodedCommand",
                base64.b64encode(script.encode("utf-16le")).decode()],
                check=True,capture_output=True,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
            with wave.open(str(path),"rb") as wav:
                data=wav.readframes(wav.getnframes())+b"\x00\x00"*16000
        owner=FakeOwner()
        recognizer=vosk.KaldiRecognizer(self.model,16000)
        wake=vosk.KaldiRecognizer(self.model,16000,json.dumps(["claire","clear","oye claire","oye clear","[unk]"]))
        wake.SetWords(True)
        engine=VoiceInput(owner,recognizer,wake_recognizer=wake)
        for start in range(0,len(data),1024):
            engine.process(data[start:start+1024],now=1+start/32000)
        return owner

    def test_synthesized_kler_wakes_and_forwards_audio(self):
        owner=self.recognize("Kler, abre Spotify")
        self.assertFalse(owner.is_sleeping)
        self.assertTrue(owner.audio)

    def test_unrelated_speech_does_not_wake(self):
        owner=self.recognize("Hola, buenas tardes")
        self.assertTrue(owner.is_sleeping)
        self.assertFalse(owner.audio)
