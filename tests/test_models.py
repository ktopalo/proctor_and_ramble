from datetime import datetime, timezone
from backend.session.models import (
    TranscriptChunk, FileDelta, Interjection,
    InterviewPlan, SessionSnapshot,
)

def test_transcript_chunk_defaults():
    chunk = TranscriptChunk(text="hello", duration_seconds=1.5)
    assert chunk.text == "hello"
    assert chunk.duration_seconds == 1.5
    assert isinstance(chunk.timestamp, datetime)

def test_file_delta_fields():
    delta = FileDelta(path="/foo/bar.py", diff="- old\n+ new")
    assert delta.path == "/foo/bar.py"
    assert "old" in delta.diff

def test_interjection_trigger():
    i = Interjection(text="Think about edge cases.", trigger="speech_pause")
    assert i.trigger == "speech_pause"

def test_interview_plan_fields():
    plan = InterviewPlan(
        problem_markdown="## Two Sum\nReturn indices of two numbers that add up to `target`.",
        follow_ups=["What if the array is sorted?", "Can you do it in O(1) space?"],
        agent_briefing="Optimal solution uses a hash map for O(n) time...",
        rubric="Strong: O(n) hash map with correct indices and edge case handling.",
    )
    assert plan.problem_markdown.startswith("## Two Sum")
    assert len(plan.follow_ups) == 2
    assert "hash map" in plan.agent_briefing
    assert isinstance(plan.rubric, str)
    assert plan.source_url is None

def test_session_snapshot_defaults():
    snap = SessionSnapshot()
    assert snap.transcript == []
    assert snap.deltas == []
    assert snap.interjections == []


def test_session_snapshot_has_revealed_follow_up_timestamps():
    snap = SessionSnapshot()
    assert snap.revealed_follow_up_timestamps == []


def test_transcript_chunk_timestamp_is_timezone_aware():
    chunk = TranscriptChunk(text="hello", duration_seconds=1.0)
    assert chunk.timestamp.tzinfo is not None


def test_file_delta_timestamp_is_timezone_aware():
    delta = FileDelta(path="/foo/bar.py", diff="+ x = 1")
    assert delta.timestamp.tzinfo is not None


def test_interjection_timestamp_is_timezone_aware():
    i = Interjection(text="Think carefully.", trigger="speech_pause")
    assert i.timestamp.tzinfo is not None
