import asyncio
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.engines.tts.tts_base import BaseTTSEngine
from backend.engines.tts.player import TTSPlayer


class _SilentEngine(BaseTTSEngine):
    async def synthesize(self, text: str) -> tuple[bytes, int]:
        samples = np.zeros(100, dtype=np.int16)
        return samples.tobytes(), 22050


@pytest.mark.asyncio
async def test_player_plays_audio_via_sounddevice():
    engine = _SilentEngine()
    with patch("backend.engines.tts.player.sd") as mock_sd:
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock()
        player = TTSPlayer(engine)
        player.start()
        await player.enqueue("Hello world")
        await player._queue.join()
        mock_sd.play.assert_called_once()
        play_args = mock_sd.play.call_args
        assert play_args.kwargs["samplerate"] == 22050
        await player.close()


@pytest.mark.asyncio
async def test_player_processes_queue_sequentially():
    call_order = []

    class _OrderEngine(BaseTTSEngine):
        async def synthesize(self, text: str) -> tuple[bytes, int]:
            call_order.append(text)
            return np.zeros(10, dtype=np.int16).tobytes(), 22050

    engine = _OrderEngine()
    with patch("backend.engines.tts.player.sd") as mock_sd:
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock()
        player = TTSPlayer(engine)
        player.start()
        await player.enqueue("first")
        await player.enqueue("second")
        await player.enqueue("third")
        await player._queue.join()
        assert call_order == ["first", "second", "third"]
        await player.close()


@pytest.mark.asyncio
async def test_player_continues_after_synthesis_error():
    succeed_calls = []

    class _FlakyEngine(BaseTTSEngine):
        def __init__(self):
            self._call = 0

        async def synthesize(self, text: str) -> tuple[bytes, int]:
            self._call += 1
            if self._call == 1:
                raise RuntimeError("API error")
            succeed_calls.append(text)
            return np.zeros(10, dtype=np.int16).tobytes(), 22050

    engine = _FlakyEngine()
    with patch("backend.engines.tts.player.sd") as mock_sd:
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock()
        player = TTSPlayer(engine)
        player.start()
        await player.enqueue("will fail")
        await player.enqueue("will succeed")
        await player._queue.join()
        assert succeed_calls == ["will succeed"]
        await player.close()
