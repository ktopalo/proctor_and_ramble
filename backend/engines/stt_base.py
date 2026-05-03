from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from backend.session.models import TranscriptChunk


class BaseSTTEngine(ABC):
    @abstractmethod
    def start(self) -> None:
        """Begin audio capture and transcription."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture and release resources."""
        ...

    @abstractmethod
    def set_on_transcript(
        self, callback: Callable[[TranscriptChunk], Awaitable[None]]
    ) -> None:
        """Register callback fired on each transcribed segment."""
        ...

    @abstractmethod
    def set_on_speech_pause(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register callback fired when silence exceeds the threshold."""
        ...
