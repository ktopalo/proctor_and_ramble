from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional


class TranscriptChunk(BaseModel):
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float


class FileDelta(BaseModel):
    path: str
    diff: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Interjection(BaseModel):
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger: str  # "speech_pause" | "file_save"


class HintStep(BaseModel):
    level: int
    text: str


class InterviewPlan(BaseModel):
    problem_statement: str
    constraints: list[str]
    hints: list[HintStep]
    expected_approaches: list[str]
    follow_up_questions: list[str]
    rubric: dict[str, str]
    source_url: Optional[str] = None


class SessionSnapshot(BaseModel):
    transcript: list[TranscriptChunk] = Field(default_factory=list)
    deltas: list[FileDelta] = Field(default_factory=list)
    interjections: list[Interjection] = Field(default_factory=list)
    plan: Optional[InterviewPlan] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    watch_path: Optional[str] = None
