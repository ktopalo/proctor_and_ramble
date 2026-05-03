import pytest
import yaml
from pathlib import Path
from backend.config import load_config, AppConfig, STTConfig, LLMConfig

def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "stt": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-mlx", "speech_pause_threshold_seconds": 3},
        "llm": {"provider": "openai", "model": "gpt-4o"},
        "agent": {"min_seconds_between_interjections": 30},
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


def test_tts_config_defaults():
    cfg = AppConfig(
        stt=STTConfig(engine="mlx_whisper", model="whisper-large-v3"),
        llm=LLMConfig(provider="openai", model="gpt-4o"),
    )
    assert cfg.tts.enabled is True
    assert cfg.tts.provider == "elevenlabs"
    assert cfg.tts.voice_id == "Rachel"
    assert cfg.tts.model_id == "eleven_monolingual_v1"
    assert cfg.tts.model_path == "models/piper/en_US-amy-medium.onnx"


def test_tts_config_loads_from_yaml(tmp_path):
    yaml_content = """
stt:
  engine: mlx_whisper
  model: whisper-large-v3
llm:
  provider: openai
  model: gpt-4o
tts:
  enabled: true
  provider: piper
  model_path: models/piper/custom.onnx
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)
    cfg = load_config(str(config_file))
    assert cfg.tts.provider == "piper"
    assert cfg.tts.model_path == "models/piper/custom.onnx"
