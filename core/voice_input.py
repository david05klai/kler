"""Local wake detection and bounded capture, independent of cloud sessions."""
from collections import deque
import json
import logging
import queue
import re
import threading
import time
import numpy as np

WAKE_RE = re.compile(r"(?<!\w)(?:kler|cler|clér|claire|clear)(?!\w)", re.IGNORECASE)
log = logging.getLogger(__name__)


def device_id(value):
    if value in ("", None, "default"):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return str(value)


class VoiceInput:
    def __init__(self, owner, recognizer=None, sample_rate=16000, blocksize=512, wake_recognizer=None):
        self.owner = owner
        self.recognizer = recognizer
        self.wake_recognizer = wake_recognizer
        self._wake_candidate = None
        self._wake_candidate_since = 0
        self._woke_this_turn = False
        self.rate, self.blocksize = sample_rate, blocksize
        self.queue = queue.Queue(maxsize=32)
        self.stop_event = threading.Event()
        self.preroll = deque(maxlen=max(1, int(sample_rate * 3 / blocksize)))
        self.dropped = 0
        self.last_level = 0
        self.last_partial = 0
        self.was_muted = False
        self.noise = deque(maxlen=50)
        self._last_noise = 0
        self.stream = None
        self.thread = threading.Thread(target=self._work, name="kler-wake", daemon=True)

    def callback(self, indata, frames, time_info, status):
        if status:
            self.owner.audio_status = str(status)
        try:
            self.queue.put_nowait(bytes(indata))
        except queue.Full:
            self.dropped += 1

    def start(self, device=None):
        import sounddevice as sd
        sd.check_input_settings(device=device_id(device), channels=1, dtype="int16", samplerate=self.rate)
        self.stream = sd.RawInputStream(device=device_id(device), samplerate=self.rate,
            channels=1, dtype="int16", blocksize=self.blocksize, callback=self.callback)
        self.thread.start()
        self.stream.start()

    def close(self):
        self.stop_event.set()
        try:
            if self.stream:
                try:
                    self.stream.stop()
                finally:
                    self.stream.close()
        finally:
            if self.thread.is_alive():
                self.thread.join(timeout=2)

    def _reset(self):
        self.preroll.clear()
        if self.recognizer:
            self.recognizer.Reset()
        if self.wake_recognizer:
            self.wake_recognizer.Reset()
        self._wake_candidate = None
        self._woke_this_turn = False

    def _work(self):
        while not self.stop_event.is_set():
            try:
                data = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.process(data)
            except Exception:
                log.exception("Local audio processing failed")
            finally:
                self.queue.task_done()

    def process(self, data, now=None):
        now = time.monotonic() if now is None else now
        owner = self.owner
        if owner.ui.muted:
            if not self.was_muted:
                self._reset()
            self.was_muted = True
            return
        self.was_muted = False
        if owner._is_speaking:
            self._reset()
            return
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(samples * samples))) / 32768 if samples.size else 0
        if now - self.last_level >= 0.05:
            owner.ui.set_audio_level(min(1, rms * 18))
            self.last_level = now
        self.preroll.append(data)
        text, final = "", False
        if self.recognizer:
            final = self.recognizer.AcceptWaveform(data)
            if final:
                text = json.loads(self.recognizer.Result()).get("text", "")
            elif owner.is_sleeping and now - self.last_partial >= 0.1:
                text = json.loads(self.recognizer.PartialResult()).get("partial", "")
                self.last_partial = now
        if owner.is_sleeping:
            wake_text = text
            stable = True
            if self.wake_recognizer:
                wake_final = self.wake_recognizer.AcceptWaveform(data)
                result = json.loads(self.wake_recognizer.Result() if wake_final else self.wake_recognizer.PartialResult())
                wake_text = result.get("text" if wake_final else "partial", "")
                match = WAKE_RE.search(wake_text)
                candidate = match.group(0).casefold() if match else None
                if candidate != self._wake_candidate:
                    self._wake_candidate = candidate
                    self._wake_candidate_since = now
                confidence = min((word.get("conf",1) for word in result.get("result",[]) if WAKE_RE.fullmatch(word.get("word",""))),default=1)
                stable = wake_final or now-self._wake_candidate_since >= 0.12
                if confidence < 0.75:
                    stable = False
            if not stable or not WAKE_RE.search(wake_text):
                return
            self._woke_this_turn = True
            owner.wake()
            owner.last_speech_time = now
            for buffered in self.preroll:
                owner.send_audio(buffered)
            self.preroll.clear()
        else:
            threshold = owner.noise_gate_threshold
            if now - self._last_noise >= 0.1:
                self.noise.append(rms)
                self._last_noise = now
            floor = min(self.noise) if self.noise else 0
            dynamic = threshold if threshold < 0.0012 else max(threshold, floor * 1.5)
            if rms > dynamic:
                owner.last_speech_time = now
            # Keep silence frames: server VAD needs them to reliably finish a turn.
            owner.send_audio(data)
            if not getattr(owner, "_is_busy", False) and now - owner.last_speech_time > owner.sleep_after:
                owner.sleep()
                self._reset()
                return
        if final and text:
            clean = WAKE_RE.sub("", text).strip(" ,.!¿?¡")
            if self._woke_this_turn:
                clean = re.sub(r"^(?:oye\s+)?(?:clara|claro|claire|clear|kler|cler)\b[\s,.]*", "", clean, flags=re.IGNORECASE)
                self._woke_this_turn = False
            if clean:
                owner.voice_text(clean)
