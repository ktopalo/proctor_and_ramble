import io
import logging
import os
import wave

import numpy as np
from groq import Groq

from backend.engines.stt.stt_base import BaseSTTEngine, _SAMPLE_RATE

log = logging.getLogger(__name__)


class GroqWhisperEngine(BaseSTTEngine):
    def __init__(self, model: str, pause_threshold_seconds: float = 1.0):
        super().__init__(pause_threshold_seconds=pause_threshold_seconds)
        self._model = model
        self._client = Groq(api_key=os.environ["GROQ_API_KEY"])
        log.info("GroqWhisperEngine  model=%s", model)

    def transcribe(self, audio: np.ndarray) -> str:
        wav_bytes = _encode_wav(audio)
        result = self._client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes, "audio/wav"),
            model=self._model,
            response_format="text",
            language="en",
        )
        return result if isinstance(result, str) else ""


def _encode_wav(audio: np.ndarray) -> bytes:
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
