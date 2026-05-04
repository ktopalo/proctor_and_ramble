import io
import wave
import httpx
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


from backend.engines.tts.elevenlabs_tts import ElevenLabsTTSEngine


@pytest.mark.asyncio
async def test_elevenlabs_synthesize_calls_api():
    fake_pcm = b"\x01\x02" * 50

    with patch("backend.engines.tts.elevenlabs_tts.httpx.AsyncClient") as MockClient:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = fake_pcm

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        engine = ElevenLabsTTSEngine(
            api_key="test_key",
            voice_id="Rachel",
            model_id="eleven_monolingual_v1",
        )
        pcm, sr = await engine.synthesize("Hello world")

    assert pcm == fake_pcm
    assert sr == 22050
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert "Rachel" in call_args.args[0]
    assert call_args.kwargs["params"]["output_format"] == "pcm_22050"
    assert call_args.kwargs["json"]["text"] == "Hello world"


@pytest.mark.asyncio
async def test_elevenlabs_raises_on_http_error():
    with patch("backend.engines.tts.elevenlabs_tts.httpx.AsyncClient") as MockClient:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        engine = ElevenLabsTTSEngine(
            api_key="bad_key",
            voice_id="Rachel",
            model_id="eleven_monolingual_v1",
        )
        with pytest.raises(httpx.HTTPStatusError):
            await engine.synthesize("Hello")


from backend.engines.tts.piper_tts import PiperTTSEngine


def test_piper_synthesize_sync_returns_pcm():
    def fake_synthesize(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(np.zeros(100, dtype=np.int16).tobytes())

    mock_voice = MagicMock()
    mock_voice.synthesize = fake_synthesize

    with patch("backend.engines.tts.piper_tts._PiperVoice") as MockPiperVoice:
        MockPiperVoice.load.return_value = mock_voice
        engine = PiperTTSEngine("dummy.onnx")
        pcm, sr = engine._synthesize_sync("Hello")

    assert sr == 22050
    assert len(pcm) == 200  # 100 samples * 2 bytes


@pytest.mark.asyncio
async def test_piper_synthesize_async():
    def fake_synthesize(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(np.zeros(50, dtype=np.int16).tobytes())

    mock_voice = MagicMock()
    mock_voice.synthesize = fake_synthesize

    with patch("backend.engines.tts.piper_tts._PiperVoice") as MockPiperVoice:
        MockPiperVoice.load.return_value = mock_voice
        engine = PiperTTSEngine("dummy.onnx")
        pcm, sr = await engine.synthesize("Hello")

    assert sr == 22050
    assert len(pcm) == 100  # 50 samples * 2 bytes
