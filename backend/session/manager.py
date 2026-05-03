from datetime import datetime, timezone
from backend.session.models import (
    TranscriptChunk, FileDelta, Interjection,
    InterviewPlan, SessionSnapshot,
)


class SessionManager:
    def __init__(self):
        self.snapshot = SessionSnapshot()

    def start(self, watch_path: str) -> None:
        self.snapshot = SessionSnapshot(
            started_at=datetime.now(timezone.utc),
            watch_path=watch_path,
            plan=self.snapshot.plan,
        )

    def end(self) -> None:
        self.snapshot.ended_at = datetime.now(timezone.utc)

    def set_plan(self, plan: InterviewPlan) -> None:
        self.snapshot.plan = plan

    def add_transcript_chunk(self, chunk: TranscriptChunk) -> None:
        self.snapshot.transcript.append(chunk)

    def add_file_delta(self, delta: FileDelta) -> None:
        self.snapshot.deltas.append(delta)

    def add_interjection(self, interjection: Interjection) -> None:
        self.snapshot.interjections.append(interjection)

    def recent_transcript_chunks(self, n: int) -> list[TranscriptChunk]:
        return self.snapshot.transcript[-n:]

    def recent_deltas(self, n: int) -> list[FileDelta]:
        return self.snapshot.deltas[-n:]
