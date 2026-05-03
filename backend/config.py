import yaml
from pydantic import BaseModel


class STTConfig(BaseModel):
    engine: str
    model: str
    speech_pause_threshold_seconds: float = 3.0


class LLMConfig(BaseModel):
    provider: str
    model: str
    codex_path: str = "codex"


class AgentConfig(BaseModel):
    min_seconds_between_interjections: int = 30


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class FrontendConfig(BaseModel):
    port: int = 5173


class TTSConfig(BaseModel):
    enabled: bool = True
    provider: str = "elevenlabs"
    voice_id: str = "Rachel"
    model_id: str = "eleven_monolingual_v1"
    model_path: str = "models/piper/en_US-amy-medium.onnx"


class AppConfig(BaseModel):
    stt: STTConfig
    llm: LLMConfig
    agent: AgentConfig = AgentConfig()
    server: ServerConfig = ServerConfig()
    frontend: FrontendConfig = FrontendConfig()
    tts: TTSConfig = TTSConfig()


def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
