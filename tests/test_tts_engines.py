import pytest
from backend.engines.tts.tts_base import BaseTTSEngine


class ConcreteTTSEngine(BaseTTSEngine):
    async def synthesize(self, text: str) -> tuple[bytes, int]:
        return b"\x00" * 100, 22050


@pytest.mark.asyncio
async def test_base_tts_engine_synthesize():
    engine = ConcreteTTSEngine()
    pcm, sr = await engine.synthesize("hello")
    assert isinstance(pcm, bytes)
    assert isinstance(sr, int)
    assert sr > 0


@pytest.mark.asyncio
async def test_base_tts_engine_close_is_noop():
    engine = ConcreteTTSEngine()
    await engine.close()  # should not raise
