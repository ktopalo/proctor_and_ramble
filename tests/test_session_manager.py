import pytest
from datetime import datetime
from backend.session.manager import SessionManager
from backend.session.models import TranscriptChunk, FileDelta, Interjection, InterviewPlan, HintStep


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
        problem_statement="Two Sum",
        constraints=[],
        hints=[HintStep(level=1, text="Use a hash map")],
        expected_approaches=["hash map"],
        follow_up_questions=[],
        rubric={"correctness": "correct"},
    )
    manager.set_plan(plan)
    assert manager.snapshot.plan.problem_statement == "Two Sum"


def test_end_sets_ended_at(manager):
    manager.start(watch_path="/foo")
    manager.end()
    assert manager.snapshot.ended_at is not None
