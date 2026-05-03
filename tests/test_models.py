from datetime import datetime
from backend.session.models import (
    TranscriptChunk, FileDelta, Interjection,
    HintStep, InterviewPlan, SessionSnapshot,
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

def test_interview_plan_required_fields():
    plan = InterviewPlan(
        problem_statement="Two Sum",
        constraints=["1 <= n <= 1000"],
        hints=[HintStep(level=1, text="Think about a hash map")],
        expected_approaches=["brute force O(n²)", "hash map O(n)"],
        follow_up_questions=["What if inputs are sorted?"],
        rubric={"correctness": "Produces correct output", "efficiency": "Optimal time"},
    )
    assert plan.problem_statement == "Two Sum"
    assert plan.hints[0].level == 1

def test_session_snapshot_defaults():
    snap = SessionSnapshot()
    assert snap.transcript == []
    assert snap.deltas == []
    assert snap.interjections == []
