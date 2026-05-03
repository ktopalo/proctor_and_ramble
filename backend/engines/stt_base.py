import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Awaitable

import numpy as np
import sounddevice as sd
import torch
from silero_vad import load_silero_vad, VADIterator

from backend.session.models import TranscriptChunk

_SAMPLE_RATE = 16000
_BLOCK_SIZE = 512  # 32ms — required by Silero VAD
_MAX_BUFFER_SECONDS = 30

log = logging.getLogger(__name__)


class BaseSTTEngine(ABC):
    def __init__(self, pause_threshold_seconds: float = 1.0):
        self._on_transcript: Callable[[TranscriptChunk], Awaitable[None]] | None = None
        self._on_speech_pause: Callable[[], Awaitable[None]] | None = None
        self._speech_buffer: list[float] = []
        self._speaking = False
        self._stream: sd.InputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        vad_model = load_silero_vad()
        self._vad_iterator = VADIterator(
            vad_model,
            threshold=0.5,
            sampling_rate=_SAMPLE_RATE,
            min_silence_duration_ms=int(pause_threshold_seconds * 1000),
            speech_pad_ms=30,
        )

    def set_on_transcript(self, callback: Callable[[TranscriptChunk], Awaitable[None]]) -> None:
        self._on_transcript = callback

    def set_on_speech_pause(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._on_speech_pause = callback

    def start(self) -> None:
        self._vad_iterator.reset_states()
        self._speech_buffer = []
        self._speaking = False

        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]
            log.info("%s starting  input=%r", self.__class__.__name__,
                     devices[default_in]["name"] if default_in >= 0 else "none")
        except Exception:
            log.info("%s starting", self.__class__.__name__)

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
            log.error("%s failed to open audio stream: %s", self.__class__.__name__, exc)
            raise

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            log.info("%s stopped", self.__class__.__name__)

    def _audio_callback(self, indata, frames, _time_info, status) -> None:
        if status:
            log.warning("%s audio status: %s", self.__class__.__name__, status)

        chunk = indata[:, 0]
        tensor = torch.from_numpy(chunk.copy())

        with self._lock:
            speech_event = self._vad_iterator(tensor)
            if speech_event:
                if "start" in speech_event:
                    self._speaking = True
                if "end" in speech_event and self._speech_buffer:
                    self._flush(pause=True)
            if self._speaking:
                self._speech_buffer.extend(chunk.tolist())
                if len(self._speech_buffer) >= _MAX_BUFFER_SECONDS * _SAMPLE_RATE:
                    self._flush(pause=False)

    def _flush(self, pause: bool) -> None:
        audio = np.array(self._speech_buffer, dtype=np.float32)
        self._speech_buffer = []
        self._speaking = False
        future = asyncio.run_coroutine_threadsafe(
            self._transcribe_and_notify(audio, pause=pause), self._loop
        )
        future.add_done_callback(_log_future_exception)

    async def _transcribe_and_notify(self, audio: np.ndarray, pause: bool) -> None:
        duration = len(audio) / _SAMPLE_RATE
        t0 = time.monotonic()
        try:
            text = self.transcribe(audio).strip()
        except Exception as exc:
            log.error("%s transcription failed  error=%s", self.__class__.__name__, exc)
            if pause and self._on_speech_pause:
                await self._on_speech_pause()
            return
        elapsed = time.monotonic() - t0
        if text:
            log.info("%s transcript  elapsed=%.2fs  text=%r", self.__class__.__name__, elapsed, text[:120])
            if self._on_transcript:
                await self._on_transcript(TranscriptChunk(text=text, duration_seconds=duration))
        else:
            log.info("%s transcript empty  elapsed=%.2fs", self.__class__.__name__, elapsed)
        if pause and self._on_speech_pause:
            await self._on_speech_pause()

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe float32 16kHz mono audio and return the text."""
        ...


def _log_future_exception(future: "asyncio.Future[None]") -> None:
    exc = future.exception()
    if exc:
        log.error("STT async dispatch raised: %s", exc)
