import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from backend.agent.loop import AgentLoop
from backend.session.manager import SessionManager
from backend.session.models import InterviewPlan, HintStep, TranscriptChunk


@pytest.fixture
def plan():
    return InterviewPlan(
        problem_statement="Two Sum",
        constraints=[],
        hints=[HintStep(level=1, text="Use a hash map")],
        expected_approaches=["hash map"],
        follow_up_questions=[],
        rubric={"correctness": "correct"},
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
