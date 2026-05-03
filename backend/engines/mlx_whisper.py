import asyncio
import logging
import threading
import time
from typing import Callable, Awaitable
import numpy as np
import sounddevice as sd
import mlx_whisper
from backend.engines.stt_base import BaseSTTEngine
from backend.session.models import TranscriptChunk

_SAMPLE_RATE = 16000
_BLOCK_SIZE = 1600  # 100ms
_SPEECH_THRESHOLD = 0.01  # RMS level above which we consider speech

log = logging.getLogger(__name__)


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
        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]
            log.info("MLXWhisper starting  model=%s  input=%r",
                     self._model, devices[default_in]["name"] if default_in >= 0 else "none")
        except Exception:
            log.info("MLXWhisper starting  model=%s", self._model)

        self._loop = asyncio.get_event_loop()
        try:
            self._stream = sd.InputStream(
                samplerate=_SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=_BLOCK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            log.error("MLXWhisper failed to open audio stream: %s", exc)
            raise

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            log.info("MLXWhisper stopped")

    def _audio_callback(self, indata, frames, _time_info, status):
        if status:
            log.warning("MLXWhisper audio status: %s", status)

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
                    future = asyncio.run_coroutine_threadsafe(
                        self._transcribe_and_notify(audio), self._loop
                    )
                    future.add_done_callback(_log_future_exception)

    async def _transcribe_and_notify(self, audio: np.ndarray) -> None:
        duration = len(audio) / _SAMPLE_RATE
        t0 = time.monotonic()
        try:
            result = mlx_whisper.transcribe(audio, path_or_hf_repo=self._model)
        except Exception as exc:
            log.error("MLXWhisper transcription failed  error=%s", exc)
            return
        elapsed = time.monotonic() - t0
        text = result.get("text", "").strip()
        if text:
            log.info("MLXWhisper transcript  elapsed=%.2fs  text=%r", elapsed, text[:120])
            if self._on_transcript:
                chunk = TranscriptChunk(text=text, duration_seconds=duration)
                await self._on_transcript(chunk)
        else:
            log.info("MLXWhisper transcript empty  elapsed=%.2fs", elapsed)
        if self._on_speech_pause:
            await self._on_speech_pause()


def _log_future_exception(future: "asyncio.Future[None]") -> None:
    exc = future.exception()
    if exc:
        log.error("MLXWhisper async dispatch raised: %s", exc)
