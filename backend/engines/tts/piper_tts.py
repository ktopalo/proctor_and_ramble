import asyncio
import io
import wave

try:
    from piper.voice import PiperVoice as _PiperVoice
except ImportError:
    _PiperVoice = None  # type: ignore[assignment,misc]

from .tts_base import BaseTTSEngine


class PiperTTSEngine(BaseTTSEngine):
    def __init__(self, model_path: str) -> None:
        if _PiperVoice is None:
            raise ImportError(
                "piper-tts is not installed. Run: pip install 'proctor_and_ramble[piper]'"
            )
        self._voice = _PiperVoice.load(model_path)

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> tuple[bytes, int]:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            self._voice.synthesize(text, wav_file)
        buf.seek(0)
        with wave.open(buf, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            pcm_bytes = wav_file.readframes(wav_file.getnframes())
        return pcm_bytes, sample_rate
