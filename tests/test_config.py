import pytest
import yaml
from pathlib import Path
from backend.config import load_config, AppConfig

def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "stt": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-mlx", "speech_pause_threshold_seconds": 3},
        "llm": {"provider": "openai", "model": "gpt-4o"},
        "agent": {"min_seconds_between_interjections": 30, "context_transcript_chunks": 20, "context_recent_deltas": 5},
        "server": {"host": "127.0.0.1", "port": 8000},
        "frontend": {"port": 5173},
    }))
    config = load_config(str(cfg_file))
    assert isinstance(config, AppConfig)
    assert config.stt.engine == "mlx_whisper"
    assert config.llm.model == "gpt-4o"
    assert config.agent.min_seconds_between_interjections == 30
    assert config.server.port == 8000

def test_load_config_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "stt": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-mlx"},
        "llm": {"provider": "openai", "model": "gpt-4o"},
    }))
    config = load_config(str(cfg_file))
    assert config.stt.speech_pause_threshold_seconds == 3.0
    assert config.agent.min_seconds_between_interjections == 30
