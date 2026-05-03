import bisect
from datetime import datetime, timezone
from pathlib import Path
from backend.session.models import (
    TranscriptChunk, FileDelta, Interjection,
    InterviewPlan, SessionSnapshot,
)


class SessionManager:
    def __init__(self):
        self.snapshot = SessionSnapshot()
        self._timeline_events: list[tuple[datetime, str]] = []

    def start(self, watch_path: str) -> None:
        self.snapshot = SessionSnapshot(
            started_at=datetime.now(timezone.utc),
            watch_path=watch_path,
            plan=self.snapshot.plan,
        )
        self._timeline_events = []

    def end(self) -> None:
        self.snapshot.ended_at = datetime.now(timezone.utc)

    def set_plan(self, plan: InterviewPlan) -> None:
        self.snapshot.plan = plan

    def _render_offset(self, ts: datetime) -> str:
        assert self.snapshot.started_at is not None
        offset = max(0, int((ts - self.snapshot.started_at).total_seconds()))
        return f"[{offset // 60:02d}:{offset % 60:02d}]"

    def add_transcript_chunk(self, chunk: TranscriptChunk) -> None:
        self.snapshot.transcript.append(chunk)
        prefix = self._render_offset(chunk.timestamp)
        line = f"{prefix} SPEECH: {chunk.text}"
        bisect.insort(self._timeline_events, (chunk.timestamp, line))

    def add_file_delta(self, delta: FileDelta) -> None:
        self.snapshot.deltas.append(delta)
        lines = delta.diff.splitlines()
        added = sum(1 for l in lines if l.startswith("+ "))
        removed = sum(1 for l in lines if l.startswith("- "))
        name = Path(delta.path).name
        indented = "\n".join("  " + l for l in lines)
        prefix = self._render_offset(delta.timestamp)
        line = f"{prefix} CODE {name} (+{added} -{removed}):\n{indented}"
        bisect.insort(self._timeline_events, (delta.timestamp, line))

    def add_interjection(self, interjection: Interjection) -> None:
        self.snapshot.interjections.append(interjection)
        prefix = self._render_offset(interjection.timestamp)
        line = f"{prefix} PROCTOR: {interjection.text}"
        bisect.insort(self._timeline_events, (interjection.timestamp, line))

    @property
    def timeline_text(self) -> str:
        if not self._timeline_events:
            return ""
        return "TIMELINE:\n" + "\n".join(line for _, line in self._timeline_events)
