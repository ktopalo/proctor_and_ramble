import pytest
from datetime import datetime, timedelta
from backend.session.manager import SessionManager
from backend.session.models import TranscriptChunk, FileDelta, Interjection, InterviewPlan


@pytest.fixture
def manager():
    return SessionManager()


def test_start_sets_started_at(manager):
    manager.start(watch_path="/foo/bar.py")
    assert manager.snapshot.started_at is not None
    assert manager.snapshot.watch_path == "/foo/bar.py"


def test_add_transcript_chunk(manager):
    manager.start(watch_path="/foo")
    chunk = TranscriptChunk(text="hello world", duration_seconds=1.0)
    manager.add_transcript_chunk(chunk)
    assert len(manager.snapshot.transcript) == 1
    assert manager.snapshot.transcript[0].text == "hello world"


def test_add_file_delta(manager):
    manager.start(watch_path="/foo")
    delta = FileDelta(path="/foo/sol.py", diff="+ x = 1")
    manager.add_file_delta(delta)
    assert len(manager.snapshot.deltas) == 1


def test_add_interjection(manager):
    manager.start(watch_path="/foo")
    i = Interjection(text="Have you thought about edge cases?", trigger="speech_pause")
    manager.add_interjection(i)
    assert len(manager.snapshot.interjections) == 1


def test_set_plan(manager):
    plan = InterviewPlan(
        problem_markdown="## Two Sum\nReturn indices.",
        follow_ups=["Follow-up 1"],
        agent_briefing="Use a hash map.",
        rubric="Correctness and efficiency.",
    )
    manager.set_plan(plan)
    assert manager.snapshot.plan.problem_markdown == "## Two Sum\nReturn indices."


def test_end_sets_ended_at(manager):
    manager.start(watch_path="/foo")
    manager.end()
    assert manager.snapshot.ended_at is not None


def test_timeline_text_empty_before_events():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    assert mgr.timeline_text == ""


def test_timeline_text_speech_format():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at
    mgr.add_transcript_chunk(TranscriptChunk(
        text="I will use a hash map", timestamp=t0 + timedelta(seconds=125), duration_seconds=2.0,
    ))
    assert "[02:05] SPEECH: I will use a hash map" in mgr.timeline_text
    assert mgr.timeline_text.startswith("TIMELINE:\n")


def test_timeline_text_code_format():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at
    mgr.add_file_delta(FileDelta(
        path="/foo/main.py", diff="+ def solve(): pass\n- pass",
        timestamp=t0 + timedelta(seconds=60),
    ))
    assert "[01:00] CODE main.py (+1 -1):" in mgr.timeline_text


def test_timeline_text_interjection_format():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at
    mgr.add_interjection(Interjection(
        text="Have you considered edge cases?",
        timestamp=t0 + timedelta(seconds=240), trigger="speech_pause",
    ))
    assert "[04:00] PROCTOR: Have you considered edge cases?" in mgr.timeline_text


def test_timeline_text_sorted_on_out_of_order_inserts():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at
    mgr.add_file_delta(FileDelta(
        path="/foo/main.py", diff="+ x = 1", timestamp=t0 + timedelta(seconds=75),
    ))
    mgr.add_transcript_chunk(TranscriptChunk(
        text="I'll use a hash map", timestamp=t0 + timedelta(seconds=42), duration_seconds=2.0,
    ))
    text = mgr.timeline_text
    assert text.index("[00:42] SPEECH:") < text.index("[01:15] CODE")


def test_timeline_events_reset_on_start():
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at
    mgr.add_transcript_chunk(TranscriptChunk(
        text="first session", timestamp=t0 + timedelta(seconds=10), duration_seconds=1.0,
    ))
    mgr.start(watch_path="/foo/main.py")
    assert mgr.timeline_text == ""


def test_reveal_next_follow_up_increments_timestamps(manager):
    manager.start(watch_path="/foo")
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 0
    manager.reveal_next_follow_up("What if sorted?")
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 1
    manager.reveal_next_follow_up("O(1) space?")
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 2


def test_reveal_next_follow_up_appears_in_timeline():
    """reveal_next_follow_up inserts a FOLLOW_UP_REVEALED entry into the timeline."""
    plan = InterviewPlan(
        problem_markdown="## Problem",
        follow_ups=["What if sorted?", "O(1) space?"],
        agent_briefing="Use hash map.",
        rubric="Correctness.",
    )
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    mgr.set_plan(plan)
    t0 = mgr.snapshot.started_at

    mgr.add_transcript_chunk(TranscriptChunk(
        text="I think I have a solution",
        timestamp=t0 + timedelta(seconds=30),
        duration_seconds=2.0,
    ))
    mgr.reveal_next_follow_up("What if sorted?")

    timeline = mgr.timeline_text
    assert "FOLLOW_UP_REVEALED: What if sorted?" in timeline
    speech_pos = timeline.index("[00:30] SPEECH:")
    reveal_pos = timeline.index("FOLLOW_UP_REVEALED:")
    assert speech_pos < reveal_pos
