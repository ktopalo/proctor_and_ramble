import pytest
from backend.engines.stt.stt_base import BaseSTTEngine
from backend.session.models import TranscriptChunk


class MockSTTEngine(BaseSTTEngine):
    def __init__(self):
        self._transcript_cb = None
        self._pause_cb = None
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def set_on_transcript(self, callback):
        self._transcript_cb = callback

    def set_on_speech_pause(self, callback):
        self._pause_cb = callback

    def transcribe(self, audio) -> str:
        return ""

    async def simulate_transcript(self, text: str):
        if self._transcript_cb:
            await self._transcript_cb(TranscriptChunk(text=text, duration_seconds=1.0))

    async def simulate_pause(self):
        if self._pause_cb:
            await self._pause_cb()


@pytest.mark.asyncio
async def test_mock_stt_fires_transcript_callback():
    received = []
    engine = MockSTTEngine()

    async def cb(chunk):
        received.append(chunk)

    engine.set_on_transcript(cb)
    await engine.simulate_transcript("hello")
    assert len(received) == 1
    assert received[0].text == "hello"


@pytest.mark.asyncio
async def test_mock_stt_fires_pause_callback():
    paused = []
    engine = MockSTTEngine()

    async def on_pause():
        paused.append(True)

    engine.set_on_speech_pause(on_pause)
    await engine.simulate_pause()
    assert paused == [True]


def test_mock_stt_lifecycle():
    engine = MockSTTEngine()
    assert not engine.started
    engine.start()
    assert engine.started
    engine.stop()
    assert not engine.started
