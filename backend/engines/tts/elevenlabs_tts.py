import httpx
from .tts_base import BaseTTSEngine

_BASE_URL = "https://api.elevenlabs.io/v1"
_SAMPLE_RATE = 22050


class ElevenLabsTTSEngine(BaseTTSEngine):
    def __init__(self, api_key: str, voice_id: str, model_id: str) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_BASE_URL}/text-to-speech/{self._voice_id}",
                headers={"xi-api-key": self._api_key},
                params={"output_format": "pcm_22050"},
                json={"text": text, "model_id": self._model_id},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.content, _SAMPLE_RATE
