import asyncio
import threading
from typing import Callable, Awaitable
import numpy as np
import sounddevice as sd
import mlx_whisper
from backend.engines.stt_base import BaseSTTEngine
from backend.session.models import TranscriptChunk

_SAMPLE_RATE = 16000
_BLOCK_SIZE = 1600  # 100ms
_SPEECH_THRESHOLD = 0.01  # RMS level above which we consider speech


class MLXWhisperEngine(BaseSTTEngine):
    def __init__(self, model: str, pause_threshold_seconds: float = 3.0):
        self._model = model
        self._pause_threshold = pause_threshold_seconds
        self._on_transcript: Callable[[TranscriptChunk], Awaitable[None]] | None = None
        self._on_speech_pause: Callable[[], Awaitable[None]] | None = None
        self._buffer: list[float] = []
        self._silence_duration = 0.0
        self._stream: sd.InputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def set_on_transcript(self, callback: Callable[[TranscriptChunk], Awaitable[None]]) -> None:
        self._on_transcript = callback

    def set_on_speech_pause(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._on_speech_pause = callback

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _audio_callback(self, indata, frames, time, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        with self._lock:
            if rms > _SPEECH_THRESHOLD:
                self._buffer.extend(indata[:, 0].tolist())
                self._silence_duration = 0.0
            else:
                self._silence_duration += frames / _SAMPLE_RATE
                if self._silence_duration >= self._pause_threshold and self._buffer:
                    audio = np.array(self._buffer, dtype=np.float32)
                    self._buffer = []
                    self._silence_duration = 0.0
                    asyncio.run_coroutine_threadsafe(
                        self._transcribe_and_notify(audio), self._loop
                    )

    async def _transcribe_and_notify(self, audio: np.ndarray) -> None:
        result = mlx_whisper.transcribe(audio, path_or_hf_repo=self._model)
        text = result.get("text", "").strip()
        if text and self._on_transcript:
            chunk = TranscriptChunk(
                text=text, duration_seconds=len(audio) / _SAMPLE_RATE
            )
            await self._on_transcript(chunk)
        if self._on_speech_pause:
            await self._on_speech_pause()
