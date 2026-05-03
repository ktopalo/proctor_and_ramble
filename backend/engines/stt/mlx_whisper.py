import logging

import mlx_whisper as _mlx_whisper
import numpy as np

from backend.engines.stt.stt_base import BaseSTTEngine

log = logging.getLogger(__name__)


class MLXWhisperEngine(BaseSTTEngine):
    def __init__(self, model: str, pause_threshold_seconds: float = 1.0):
        super().__init__(pause_threshold_seconds=pause_threshold_seconds)
        self._model = model
        log.info("MLXWhisperEngine  model=%s", model)

    def transcribe(self, audio: np.ndarray) -> str:
        result = _mlx_whisper.transcribe(audio, path_or_hf_repo=self._model)
        return result.get("text", "")
