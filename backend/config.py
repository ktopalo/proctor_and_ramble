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
    context_transcript_chunks: int = 20
    context_recent_deltas: int = 5


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class FrontendConfig(BaseModel):
    port: int = 5173


class AppConfig(BaseModel):
    stt: STTConfig
    llm: LLMConfig
    agent: AgentConfig = AgentConfig()
    server: ServerConfig = ServerConfig()
    frontend: FrontendConfig = FrontendConfig()


def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
