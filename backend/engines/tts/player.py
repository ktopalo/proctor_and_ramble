import asyncio
import logging

import numpy as np
import sounddevice as sd

from .tts_base import BaseTTSEngine

log = logging.getLogger(__name__)


class TTSPlayer:
    def __init__(self, engine: BaseTTSEngine) -> None:
        self._engine = engine
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._worker())

    async def enqueue(self, text: str) -> None:
        self._queue.put_nowait(text)

    async def _worker(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            text = await self._queue.get()
            try:
                pcm_bytes, sample_rate = await self._engine.synthesize(text)
                audio = np.frombuffer(pcm_bytes, dtype=np.int16)
                sd.play(audio, samplerate=sample_rate)
                await loop.run_in_executor(None, sd.wait)
            except asyncio.CancelledError:
                self._queue.task_done()
                raise
            except Exception:
                log.exception("TTS playback failed")
            finally:
                self._queue.task_done()

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._engine.close()
