# Agent Loop Chronological Context — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the agent loop's two disconnected context buckets with a single chronological timeline that interleaves speech, code, and prior proctor interjections by timestamp.

**Architecture:** `_build_context` in `AgentLoop` merges all three event types from `SessionManager` into a list sorted by `timestamp`, then renders them as `[MM:SS] LABEL: content` entries. A prerequisite fix in `models.py` makes all event timestamps timezone-aware so elapsed-time arithmetic works correctly.

**Tech Stack:** Python, pytest, `datetime.timezone`, `pathlib.Path`

---

## Files

| File | Change |
|---|---|
| `backend/session/models.py` | Change all three `default_factory=datetime.utcnow` to `lambda: datetime.now(timezone.utc)` |
| `backend/agent/loop.py` | Rewrite `_build_context` only |
| `tests/test_models.py` | Add timezone-awareness assertions |
| `tests/test_agent_loop.py` | Add `_build_context` tests |

---

## Task 1: Fix naive datetimes in models.py

The three event models use `datetime.utcnow` (naive) as their timestamp factory. `SessionManager.start()` now uses `datetime.now(timezone.utc)` (aware). Subtracting naive from aware crashes — fix before implementing the timeline.

**Files:**
- Modify: `backend/session/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add failing tests to `tests/test_models.py`**

Add these three tests to the existing file. They assert `.tzinfo is not None` (timezone-aware):

```python
from datetime import timezone

def test_transcript_chunk_timestamp_is_timezone_aware():
    chunk = TranscriptChunk(text="hello", duration_seconds=1.0)
    assert chunk.timestamp.tzinfo is not None

def test_file_delta_timestamp_is_timezone_aware():
    delta = FileDelta(path="/foo/bar.py", diff="+ x = 1")
    assert delta.timestamp.tzinfo is not None

def test_interjection_timestamp_is_timezone_aware():
    i = Interjection(text="Think carefully.", trigger="speech_pause")
    assert i.timestamp.tzinfo is not None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_models.py::test_transcript_chunk_timestamp_is_timezone_aware tests/test_models.py::test_file_delta_timestamp_is_timezone_aware tests/test_models.py::test_interjection_timestamp_is_timezone_aware -v
```

Expected: all three FAIL — `assert None is not None`

- [ ] **Step 3: Fix `backend/session/models.py`**

Replace the file with this content:

```python
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
```

- [ ] **Step 4: Run all three new tests to confirm they pass**

```bash
pytest tests/test_models.py::test_transcript_chunk_timestamp_is_timezone_aware tests/test_models.py::test_file_delta_timestamp_is_timezone_aware tests/test_models.py::test_interjection_timestamp_is_timezone_aware -v
```

Expected: all three PASS

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/session/models.py tests/test_models.py
git commit -m "fix: timezone-aware timestamps in session models"
```

---

## Task 2: Rewrite `_build_context` in `loop.py`

Replace the two-bucket context with a chronological interleaved timeline. The `TIMELINE:` block merges all `TranscriptChunk`, `FileDelta`, and `Interjection` entries sorted by timestamp. Each entry gets a `[MM:SS]` prefix relative to `session.started_at`.

**Files:**
- Modify: `backend/agent/loop.py`
- Modify: `tests/test_agent_loop.py`

- [ ] **Step 1: Add failing tests to `tests/test_agent_loop.py`**

The existing file already imports `from datetime import datetime, timedelta` and `from unittest.mock import AsyncMock`. Change that datetime import line to also include `timezone`, and add the two missing model imports:

```python
# change this existing line:
from datetime import datetime, timedelta
# to:
from datetime import datetime, timedelta, timezone

# add these two new imports alongside the existing model imports:
from backend.session.models import FileDelta, Interjection
```

Then add these four tests at the bottom of the file:

```python
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
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
pytest tests/test_agent_loop.py::test_build_context_chronological_ordering tests/test_agent_loop.py::test_build_context_event_labels tests/test_agent_loop.py::test_build_context_mm_ss_format tests/test_agent_loop.py::test_build_context_no_timeline_when_empty -v
```

Expected: all four FAIL (old `_build_context` produces wrong output format)

- [ ] **Step 3: Rewrite `_build_context` in `backend/agent/loop.py`**

Replace the existing `_build_context` method with:

```python
def _build_context(self) -> str:
    from pathlib import Path
    snap = self._session.snapshot

    parts = []

    if snap.plan:
        parts.append(f"PROBLEM: {snap.plan.problem_statement}")
        if snap.plan.constraints:
            parts.append("CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in snap.plan.constraints))
        if snap.plan.hints:
            hints_text = "\n".join(f"- (level {h.level}) {h.text}" for h in snap.plan.hints)
            parts.append(f"HINTS (for your reference only — do not reveal):\n{hints_text}")

    if snap.started_at:
        secs = int((datetime.now(timezone.utc) - snap.started_at).total_seconds())
        parts.append(f"TIME ELAPSED: {secs // 60}m {secs % 60}s")

    events: list[tuple[datetime, str]] = []

    for chunk in snap.transcript:
        events.append((chunk.timestamp, f"SPEECH: {chunk.text}"))

    for delta in snap.deltas:
        lines = delta.diff.splitlines()
        added = sum(1 for l in lines if l.startswith("+ "))
        removed = sum(1 for l in lines if l.startswith("- "))
        name = Path(delta.path).name
        indented = "\n".join("  " + l for l in lines)
        events.append((delta.timestamp, f"CODE {name} (+{added} -{removed}):\n{indented}"))

    for interjection in snap.interjections:
        events.append((interjection.timestamp, f"PROCTOR: {interjection.text}"))

    events.sort(key=lambda e: e[0])

    if events:
        timeline_lines = []
        for ts, content in events:
            if snap.started_at:
                offset = max(0, int((ts - snap.started_at).total_seconds()))
                prefix = f"[{offset // 60:02d}:{offset % 60:02d}]"
            else:
                prefix = "[??:??]"
            timeline_lines.append(f"{prefix} {content}")
        parts.append("TIMELINE:\n" + "\n".join(timeline_lines))

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run all four new tests to confirm they pass**

```bash
pytest tests/test_agent_loop.py::test_build_context_chronological_ordering tests/test_agent_loop.py::test_build_context_event_labels tests/test_agent_loop.py::test_build_context_mm_ss_format tests/test_agent_loop.py::test_build_context_no_timeline_when_empty -v
```

Expected: all four PASS

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/agent/loop.py tests/test_agent_loop.py
git commit -m "feat: chronological interleaved timeline in agent loop context"
```
