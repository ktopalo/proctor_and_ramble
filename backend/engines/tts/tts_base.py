from abc import ABC, abstractmethod


class BaseTTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Convert text to speech. Returns (raw PCM bytes, sample_rate_hz)."""
        ...

    async def close(self) -> None:
        pass
