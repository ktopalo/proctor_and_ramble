from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        """Send messages and return the full completion."""
        ...

    @abstractmethod
    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        """Send messages and stream the completion token by token."""
        ...
