import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from backend.agent.loop import AgentLoop
from backend.session.manager import SessionManager
from backend.session.models import InterviewPlan, TranscriptChunk, FileDelta, Interjection


@pytest.fixture
def plan():
    return InterviewPlan(
        problem_markdown="## Two Sum\nReturn indices of two numbers that add up to target.",
        follow_ups=["What if the array is sorted?"],
        agent_briefing="Use a hash map for O(n) solution.",
        rubric="Correctness and efficiency.",
    )


@pytest.fixture
def session(plan):
    mgr = SessionManager()
    mgr.start(watch_path="/foo/bar.py")
    mgr.set_plan(plan)
    for i in range(3):
        mgr.add_transcript_chunk(TranscriptChunk(text=f"chunk {i}", duration_seconds=1.0))
    return mgr


@pytest.mark.asyncio
async def test_agent_intervenes_when_llm_says_yes(session):
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Have you considered what happens with duplicates?")
    emitted = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: emitted.append(i),
    )

    await loop.on_speech_pause()

    assert len(emitted) == 1
    assert "duplicates" in emitted[0].text
    assert emitted[0].trigger == "speech_pause"
    assert len(session.snapshot.interjections) == 1


@pytest.mark.asyncio
async def test_agent_silent_when_llm_says_no(session):
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="NO")
    emitted = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: emitted.append(i),
    )

    await loop.on_speech_pause()

    assert len(emitted) == 0
    assert len(session.snapshot.interjections) == 0


@pytest.mark.asyncio
async def test_agent_respects_cooldown(session):
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Think about edge cases.")
    emitted = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=60,
        on_interjection=lambda i: emitted.append(i),
    )

    await loop.on_speech_pause()
    await loop.on_file_save()

    assert len(emitted) == 1
    assert mock_llm.complete.call_count == 1


@pytest.mark.asyncio
async def test_agent_file_save_trigger(session):
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Interesting approach — what's the time complexity?")
    emitted = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: emitted.append(i),
    )

    await loop.on_file_save()

    assert len(emitted) == 1
    assert emitted[0].trigger == "file_save"


def test_build_context_chronological_ordering():
    """Events added out of order should appear sorted by timestamp in the timeline."""
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at

    # Add deliberately out of order: delta first, then earlier speech
    mgr.add_file_delta(FileDelta(
        path="/foo/main.py", diff="+ x = 1",
        timestamp=t0 + timedelta(seconds=75),
    ))
    mgr.add_transcript_chunk(TranscriptChunk(
        text="I'll use a hash map",
        timestamp=t0 + timedelta(seconds=42),
        duration_seconds=2.0,
    ))
    mgr.add_interjection(Interjection(
        text="Have you considered edge cases?",
        timestamp=t0 + timedelta(seconds=240),
        trigger="speech_pause",
    ))

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    speech_pos = context.index("[00:42] SPEECH:")
    code_pos = context.index("[01:15] CODE")
    proctor_pos = context.index("[04:00] PROCTOR:")
    assert speech_pos < code_pos < proctor_pos


def test_build_context_event_labels():
    """All three event types appear with correct labels and content."""
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at

    mgr.add_transcript_chunk(TranscriptChunk(
        text="thinking aloud", timestamp=t0 + timedelta(seconds=10), duration_seconds=1.0,
    ))
    mgr.add_file_delta(FileDelta(
        path="/foo/main.py", diff="+ def solve(): pass",
        timestamp=t0 + timedelta(seconds=20),
    ))
    mgr.add_interjection(Interjection(
        text="What's the time complexity?",
        timestamp=t0 + timedelta(seconds=30),
        trigger="speech_pause",
    ))

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    assert "SPEECH: thinking aloud" in context
    assert "CODE main.py" in context
    assert "PROCTOR: What's the time complexity?" in context


def test_build_context_mm_ss_format():
    """Elapsed timestamps render as [MM:SS] relative to session start."""
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at

    mgr.add_transcript_chunk(TranscriptChunk(
        text="hello", timestamp=t0 + timedelta(seconds=125), duration_seconds=1.0,
    ))

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    assert "[02:05] SPEECH: hello" in context


def test_build_context_no_timeline_when_empty():
    """No TIMELINE section when the session has no events yet."""
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    assert "TIMELINE" not in context
