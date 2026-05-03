# Question Enrichment Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `InterviewPlan` structure with a two-zone model (display markdown + rich agent briefing) and wire up a progressive follow-up reveal mechanic via a new WebSocket event.

**Architecture:** New `InterviewPlan` has four fields (`problem_markdown`, `follow_ups`, `agent_briefing`, `rubric`). The agent loop dynamically builds its system prompt by appending the briefing to the static proctor instructions. Follow-up reveals are tracked as a timestamp list on `SessionSnapshot` and broadcast as `follow_up_revealed` WS events.

**Tech Stack:** Python/Pydantic (backend models), FastAPI (WS broadcast), TypeScript/React (frontend), `react-markdown` via existing `MarkdownText` component (already installed).

---

## File Map

| File | Action | What changes |
|---|---|---|
| `backend/session/models.py` | Modify | New `InterviewPlan` fields; `revealed_follow_up_timestamps` on `SessionSnapshot`; remove `HintStep` |
| `backend/session/manager.py` | Modify | Add `reveal_next_follow_up()` method |
| `backend/question/loader.py` | Modify | New extraction + system prompts; truncation 8000→12000 |
| `backend/agent/prompts.py` | Modify | Add `REVEAL_NEXT_FOLLOWUP` paragraph to proctor instructions |
| `backend/agent/loop.py` | Modify | Dynamic system prompt; new `_build_context`; `REVEAL_NEXT_FOLLOWUP` parsing; `on_follow_up_revealed` callback |
| `backend/main.py` | Modify | Wire `on_follow_up_revealed`; update feedback endpoint; update log line |
| `frontend/src/types/session.ts` | Modify | New `InterviewPlan`; `revealed_follow_up_timestamps` on snapshot; `follow_up_revealed` WS event type |
| `frontend/src/hooks/useSession.ts` | Modify | Handle `follow_up_revealed` event; update `EMPTY_SNAPSHOT` |
| `frontend/src/components/QuestionPanel.tsx` | Modify | Render `problem_markdown` via `MarkdownText`; progressive follow-up blocks; new `revealedCount` prop |
| `frontend/src/screens/Interview.tsx` | Modify | Pass `revealedCount` to `QuestionPanel` |
| `frontend/src/screens/Setup.tsx` | Modify | Redesign `QuestionPreview` for new `InterviewPlan` shape |
| `tests/test_models.py` | Modify | Update `InterviewPlan` tests; remove `HintStep` test; add `revealed_follow_up_timestamps` test |
| `tests/test_session_manager.py` | Modify | Add `reveal_next_follow_up` test |
| `tests/test_question_loader.py` | Modify | Update mock LLM response + assertions for new fields |
| `tests/test_agent_loop.py` | Modify | Update `plan` fixture; add `REVEAL_NEXT_FOLLOWUP` signal tests; add `FOLLOW_UP_REVEALED` timeline test |

---

## Task 1: Update Backend Models

**Files:**
- Modify: `backend/session/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for the new model shape**

In `tests/test_models.py`, replace the `test_interview_plan_required_fields` test and add new ones. The full updated test file (keep existing `TranscriptChunk`, `FileDelta`, `Interjection`, `SessionSnapshot` tests unchanged):

```python
# replace test_interview_plan_required_fields with:
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


def test_session_snapshot_has_revealed_follow_up_timestamps():
    snap = SessionSnapshot()
    assert snap.revealed_follow_up_timestamps == []
```

Also remove the import of `HintStep` from the test file's import line since that class is being removed.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble
python -m pytest tests/test_models.py -v 2>&1 | tail -20
```

Expected: FAIL — `InterviewPlan` still has old fields, `HintStep` still exists, `revealed_follow_up_timestamps` doesn't exist.

- [ ] **Step 3: Update `backend/session/models.py`**

Replace the entire file:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TranscriptChunk(BaseModel):
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float


class FileDelta(BaseModel):
    path: str
    diff: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Interjection(BaseModel):
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trigger: str  # "speech_pause" | "file_save"


class InterviewPlan(BaseModel):
    problem_markdown: str
    follow_ups: list[str]
    agent_briefing: str
    rubric: str
    source_url: Optional[str] = None


class SessionSnapshot(BaseModel):
    transcript: list[TranscriptChunk] = Field(default_factory=list)
    deltas: list[FileDelta] = Field(default_factory=list)
    interjections: list[Interjection] = Field(default_factory=list)
    plan: Optional[InterviewPlan] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    watch_path: Optional[str] = None
    revealed_follow_up_timestamps: list[datetime] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_models.py -v 2>&1 | tail -20
```

Expected: All tests in `test_models.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/session/models.py tests/test_models.py
git commit -m "feat: replace InterviewPlan with two-zone model, add reveal timestamps"
```

---

## Task 2: Update SessionManager

**Files:**
- Modify: `backend/session/manager.py`
- Modify: `tests/test_session_manager.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_session_manager.py`:

```python
def test_reveal_next_follow_up(manager):
    manager.start(watch_path="/foo")
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 0
    manager.reveal_next_follow_up()
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 1
    manager.reveal_next_follow_up()
    assert len(manager.snapshot.revealed_follow_up_timestamps) == 2
```

Also update `test_set_plan` to use the new `InterviewPlan` fields — replace the existing test body:

```python
def test_set_plan(manager):
    plan = InterviewPlan(
        problem_markdown="## Two Sum\nReturn indices.",
        follow_ups=["Follow-up 1"],
        agent_briefing="Use a hash map.",
        rubric="Correctness and efficiency.",
    )
    manager.set_plan(plan)
    assert manager.snapshot.plan.problem_markdown == "## Two Sum\nReturn indices."
```

Remove the `HintStep` import from `tests/test_session_manager.py` — update the import line to:

```python
from backend.session.models import TranscriptChunk, FileDelta, Interjection, InterviewPlan
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_session_manager.py -v 2>&1 | tail -20
```

Expected: FAIL — `reveal_next_follow_up` method doesn't exist yet.

- [ ] **Step 3: Update `backend/session/manager.py`**

```python
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

    def reveal_next_follow_up(self) -> None:
        self.snapshot.revealed_follow_up_timestamps.append(datetime.now(timezone.utc))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_session_manager.py -v 2>&1 | tail -20
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/session/manager.py tests/test_session_manager.py
git commit -m "feat: add reveal_next_follow_up to SessionManager"
```

---

## Task 3: Update Question Loader

**Files:**
- Modify: `backend/question/loader.py`
- Modify: `tests/test_question_loader.py`

- [ ] **Step 1: Write the failing tests**

Replace the entire `tests/test_question_loader.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.question.loader import load_question
from backend.session.models import InterviewPlan


MOCK_LLM_RESPONSE = json.dumps({
    "problem_markdown": "## Two Sum\n\nGiven an array of integers `nums` and an integer `target`, return **indices** of the two numbers such that they add up to `target`.\n\n```python\nnums = [2, 7, 11, 15]\ntarget = 9\n# Output: [0, 1]\n```",
    "follow_ups": [
        "What if the array is sorted? Can you do better than O(n) space?",
        "Now handle the case where there may be multiple valid answers.",
    ],
    "agent_briefing": "Brute force: O(n²) nested loops. Optimal: hash map O(n) time and space — store complement as key. Common mistake: returning values not indices. Edge case: same element used twice (e.g. [3,3], target=6). Reveal follow-up 1 once candidate has a working solution.",
    "rubric": "Strong: O(n) hash map, correct indices, handles duplicates, explains complexity. Weak: brute force only, no edge case reasoning.",
})


@pytest.mark.asyncio
async def test_load_question_returns_interview_plan():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    mock_html = "<html><body><p>Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.</p></body></html>"

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        plan = await load_question("https://leetcode.com/problems/two-sum/", mock_llm)

    assert isinstance(plan, InterviewPlan)
    assert "Two Sum" in plan.problem_markdown
    assert len(plan.follow_ups) == 2
    assert "hash map" in plan.agent_briefing
    assert isinstance(plan.rubric, str)
    assert plan.source_url == "https://leetcode.com/problems/two-sum/"


@pytest.mark.asyncio
async def test_load_question_passes_url_to_plan():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<p>some problem</p>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        plan = await load_question("https://example.com/problem/123", mock_llm)

    assert plan.source_url == "https://example.com/problem/123"


@pytest.mark.asyncio
async def test_load_question_truncates_page_at_12000():
    """Page content is truncated at 12000 chars before being sent to the LLM."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    long_page = "<p>" + "x" * 20000 + "</p>"

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = long_page
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        await load_question("https://example.com/", mock_llm)

    call_args = mock_llm.complete.call_args
    user_content = call_args.kwargs["messages"][0]["content"]
    assert len(user_content) <= len("You are preparing a technical coding interview brief") + 12000 + 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_question_loader.py -v 2>&1 | tail -20
```

Expected: FAIL — loader still returns old `InterviewPlan` shape.

- [ ] **Step 3: Update `backend/question/loader.py`**

```python
import json
import logging
from html.parser import HTMLParser
import httpx
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import InterviewPlan

log = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


_EXTRACTION_PROMPT = """\
You are preparing a technical coding interview brief for a software engineering candidate. \
Extract the coding problem from the page content below and produce a rich interview plan. \
Return ONLY valid JSON with exactly these fields:

{
  "problem_markdown": "The complete problem description in markdown. Include the problem statement, \
any code snippets as fenced code blocks, and any constraints that are immediately relevant to solving \
the problem. Write this exactly as the candidate will read it during the interview.",
  "follow_ups": [
    "A markdown string for the first deferred challenge or constraint to reveal (gentlest — e.g. a follow-on constraint or small twist)",
    "A markdown string for the next challenge (harder — e.g. a stricter complexity requirement or a variant)",
    "..."
  ],
  "agent_briefing": "A thorough prose briefing a senior software engineer would write before running \
this interview. Cover: all known approaches from brute-force to optimal with their time and space \
complexity; the most common mistakes candidates make; subtle gotchas and edge cases the candidate \
is likely to miss; what strong vs weak performance looks like at each stage of the interview; and \
specific guidance on when to surface each follow-up (e.g. reveal follow-up 1 once the candidate has \
a working brute-force solution). No length limit — be thorough.",
  "rubric": "A free-form evaluation guide describing what a strong submission looks like. Cover: \
correctness, time and space efficiency, code quality, communication and reasoning while coding, \
and edge case handling."
}

Page content:
"""

_SYSTEM_PROMPT = (
    "You are an expert software engineering interviewer preparing a structured brief for a live "
    "technical coding interview. The candidate is a software engineer. "
    "Return only valid JSON, no markdown fences."
)


async def load_question(url: str, llm: BaseLLMClient) -> InterviewPlan:
    log.info("Fetching question  url=%s", url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    page_text = extractor.text[:12000]

    raw = await llm.complete(
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + page_text}],
        system_prompt=_SYSTEM_PROMPT,
    )

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        log.error("Failed to parse LLM JSON response  error=%s  raw=%r", exc, raw[:200])
        raise

    plan = InterviewPlan(**data, source_url=url)
    log.info("InterviewPlan created  problem=%s", plan.problem_markdown[:80])
    return plan
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_question_loader.py -v 2>&1 | tail -20
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/question/loader.py tests/test_question_loader.py
git commit -m "feat: redesign question loader with two-zone extraction prompt"
```

---

## Task 4: Update Agent Prompts

**Files:**
- Modify: `backend/agent/prompts.py`

- [ ] **Step 1: Update `backend/agent/prompts.py`**

Append the `REVEAL_NEXT_FOLLOWUP` instructions to the existing `PROCTOR_SYSTEM_PROMPT`. Replace the file:

```python
PROCTOR_SYSTEM_PROMPT = """\
You are a proctor for a software engineering coding interview. Your role is to evaluate \
the candidate — not to teach, coach, or assist them. The candidate is expected to solve \
the problem on their own.

You observe their speech and code changes in real time. You also have a full interview brief \
(approaches, gotchas, follow-ups) and the elapsed interview time.

Default behavior: stay silent. Return exactly "NO".

Only intervene when one of these is clearly true:
- The candidate has been stuck with no meaningful code or verbal progress for a significant \
portion of the interview
- The candidate is pursuing a fundamentally broken approach and time pressure makes a small \
redirect worthwhile
- The candidate explicitly signals they are lost or asks for help or is clearly talking to you the proctor

When intervening unprompted (stuck or wrong direction):
- One Socratic question or a single directional sentence — nothing more
- Never reveal the answer, the expected approach, or steps toward it
- Do not validate or evaluate their current direction — that is for the debrief
- Neutral and professional tone

When the candidate is directly asking you for help:
- Respond the way a real interviewer would: engaged, human, willing to clarify the problem or \
confirm they understand the constraints correctly
- You can acknowledge where they are, restate the problem from a different angle, or ask a \
guiding question — but still do not hand them the solution
- A short, natural conversational response is appropriate here

Revealing follow-ups:
- Follow-ups are deferred constraints or challenges that extend the problem. They are revealed \
one at a time when the candidate earns them (e.g. by solving the base problem or asking a \
question that warrants it). Your interview brief describes when each one should be surfaced.
- To reveal the next follow-up, respond with exactly: REVEAL_NEXT_FOLLOWUP
- To reveal the next follow-up AND say something, respond with: REVEAL_NEXT_FOLLOWUP: <your message>
- Never reveal a follow-up when none remain (check FOLLOW-UPS REVEALED in context).

Respond with exactly "NO", the interjection text, or a REVEAL_NEXT_FOLLOWUP line. No preamble.\
"""

PROMPTS: dict[str, str] = {
    "proctor": PROCTOR_SYSTEM_PROMPT,
}


def get_prompt(name: str = "proctor") -> str:
    if name not in PROMPTS:
        raise ValueError(f"Unknown prompt persona: {name!r}. Available: {list(PROMPTS)}")
    return PROMPTS[name]
```

- [ ] **Step 2: Verify no test failures introduced**

```bash
python -m pytest tests/ -v --ignore=tests/test_agent_loop.py 2>&1 | tail -20
```

Expected: All tests outside `test_agent_loop.py` PASS. (`test_agent_loop.py` uses old `InterviewPlan` fields and will be fixed in Task 5.)

- [ ] **Step 3: Commit**

```bash
git add backend/agent/prompts.py
git commit -m "feat: add REVEAL_NEXT_FOLLOWUP instructions to proctor prompt"
```

---

## Task 5: Update Agent Loop

**Files:**
- Modify: `backend/agent/loop.py`
- Modify: `tests/test_agent_loop.py`

- [ ] **Step 1: Write failing tests**

Replace the entire `tests/test_agent_loop.py`:

```python
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
        problem_markdown="## Two Sum\nReturn indices of two numbers that add up to `target`.",
        follow_ups=["What if the array is sorted?", "Can you solve it in O(1) space?"],
        agent_briefing="Optimal solution is a hash map for O(n) time and O(n) space. Brute force is O(n²). Common mistake: returning values not indices. Edge case: same index used twice.",
        rubric="Strong: O(n) hash map, correct indices, edge cases handled.",
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


@pytest.mark.asyncio
async def test_reveal_next_followup_increments_count(session):
    """REVEAL_NEXT_FOLLOWUP increments revealed count and calls the callback."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="REVEAL_NEXT_FOLLOWUP")
    revealed = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: None,
        on_follow_up_revealed=lambda: revealed.append(True),
    )

    await loop.on_speech_pause()

    assert len(session.snapshot.revealed_follow_up_timestamps) == 1
    assert len(revealed) == 1


@pytest.mark.asyncio
async def test_reveal_next_followup_with_interjection(session):
    """REVEAL_NEXT_FOLLOWUP: <text> both reveals and emits an interjection."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="REVEAL_NEXT_FOLLOWUP: Now let's add a twist.")
    emitted = []
    revealed = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: emitted.append(i),
        on_follow_up_revealed=lambda: revealed.append(True),
    )

    await loop.on_speech_pause()

    assert len(session.snapshot.revealed_follow_up_timestamps) == 1
    assert len(revealed) == 1
    assert len(emitted) == 1
    assert emitted[0].text == "Now let's add a twist."


@pytest.mark.asyncio
async def test_reveal_next_followup_does_not_exceed_total(session):
    """Agent cannot reveal more follow-ups than exist."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="REVEAL_NEXT_FOLLOWUP")
    revealed = []

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: None,
        on_follow_up_revealed=lambda: revealed.append(True),
    )

    # session.plan has 2 follow_ups — try to reveal 3 times
    await loop.on_speech_pause()
    loop._last_interjection_at = None  # reset cooldown
    await loop.on_speech_pause()
    loop._last_interjection_at = None
    await loop.on_speech_pause()

    assert len(session.snapshot.revealed_follow_up_timestamps) == 2
    assert len(revealed) == 2


@pytest.mark.asyncio
async def test_system_prompt_includes_agent_briefing(session):
    """agent_briefing and rubric are appended to the system prompt."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="NO")

    loop = AgentLoop(
        session=session,
        llm=mock_llm,
        min_interjection_gap_seconds=0,
        on_interjection=lambda i: None,
    )

    await loop.on_speech_pause()

    call_kwargs = mock_llm.complete.call_args.kwargs
    system_prompt = call_kwargs["system_prompt"]
    assert "INTERVIEW BRIEF:" in system_prompt
    assert "hash map" in system_prompt  # from agent_briefing fixture
    assert "RUBRIC:" in system_prompt


def test_build_context_chronological_ordering():
    """Events added out of order should appear sorted by timestamp in the timeline."""
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    t0 = mgr.snapshot.started_at

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


def test_build_context_includes_follow_up_revealed_event():
    """A revealed follow-up appears in the timeline at its reveal timestamp."""
    plan = InterviewPlan(
        problem_markdown="## Problem",
        follow_ups=["What if sorted?"],
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
    # Manually inject a reveal timestamp (normally done by reveal_next_follow_up)
    mgr.snapshot.revealed_follow_up_timestamps.append(t0 + timedelta(seconds=60))

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    assert "FOLLOW_UP_REVEALED" in context
    speech_pos = context.index("[00:30] SPEECH:")
    reveal_pos = context.index("[01:00] FOLLOW_UP_REVEALED:")
    assert speech_pos < reveal_pos


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


def test_build_context_has_follow_up_state_header():
    """Context includes FOLLOW-UPS REVEALED count when a plan is loaded."""
    plan = InterviewPlan(
        problem_markdown="## Problem",
        follow_ups=["Follow-up 1", "Follow-up 2"],
        agent_briefing="Brief.",
        rubric="Rubric.",
    )
    mgr = SessionManager()
    mgr.start(watch_path="/foo/main.py")
    mgr.set_plan(plan)

    loop = AgentLoop(
        session=mgr, llm=AsyncMock(),
        min_interjection_gap_seconds=0, on_interjection=lambda i: None,
    )
    context = loop._build_context()

    assert "FOLLOW-UPS REVEALED: 0 of 2" in context
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_agent_loop.py -v 2>&1 | tail -30
```

Expected: FAIL — `AgentLoop` doesn't have `on_follow_up_revealed`, system prompt doesn't include briefing, `_build_context` still has old PROBLEM block.

- [ ] **Step 3: Update `backend/agent/loop.py`**

```python
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from backend.session.manager import SessionManager
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import Interjection
from backend.agent.prompts import get_prompt

log = logging.getLogger(__name__)


class AgentLoop:
    def __init__(
        self,
        session: SessionManager,
        llm: BaseLLMClient,
        min_interjection_gap_seconds: int,
        on_interjection: Callable[[Interjection], None],
        on_follow_up_revealed: Callable[[], None] = lambda: None,
    ):
        self._session = session
        self._llm = llm
        self._gap = min_interjection_gap_seconds
        self._on_interjection = on_interjection
        self._on_follow_up_revealed = on_follow_up_revealed
        self._last_interjection_at: datetime | None = None

    async def on_speech_pause(self) -> None:
        log.debug("AgentLoop trigger: speech_pause")
        await self._maybe_intervene(trigger="speech_pause")

    async def on_file_save(self) -> None:
        log.debug("AgentLoop trigger: file_save")
        await self._maybe_intervene(trigger="file_save")

    def _cooldown_active(self) -> bool:
        if self._last_interjection_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._last_interjection_at).total_seconds()
        return elapsed < self._gap

    def _build_context(self) -> str:
        snap = self._session.snapshot
        plan = snap.plan

        parts = []

        if snap.started_at:
            secs = int((datetime.now(timezone.utc) - snap.started_at).total_seconds())
            parts.append(f"TIME ELAPSED: {secs // 60}m {secs % 60}s")

        if plan:
            total = len(plan.follow_ups)
            revealed = len(snap.revealed_follow_up_timestamps)
            parts.append(f"FOLLOW-UPS REVEALED: {revealed} of {total}")

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

        if plan:
            for i, ts in enumerate(snap.revealed_follow_up_timestamps):
                if i < len(plan.follow_ups):
                    events.append((ts, f"FOLLOW_UP_REVEALED: {plan.follow_ups[i]}"))

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

    async def _maybe_intervene(self, trigger: str) -> None:
        if self._cooldown_active():
            elapsed = (datetime.now(timezone.utc) - self._last_interjection_at).total_seconds()
            log.info("AgentLoop cooldown  trigger=%s  elapsed=%.0fs/%.0fs", trigger, elapsed, self._gap)
            return

        snap = self._session.snapshot
        log.info("AgentLoop evaluating  trigger=%s  transcript_chunks=%d  deltas=%d",
                 trigger, len(snap.transcript), len(snap.deltas))

        system_prompt = get_prompt()
        if snap.plan:
            system_prompt = (
                f"{system_prompt}\n\n---\n\n"
                f"INTERVIEW BRIEF:\n{snap.plan.agent_briefing}\n\n"
                f"RUBRIC:\n{snap.plan.rubric}"
            )

        context = self._build_context()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": context}],
            system_prompt=system_prompt,
        )

        log.info("AgentLoop LLM response  %r", response.strip()[:200])

        if response.strip().upper().startswith("REVEAL_NEXT_FOLLOWUP"):
            plan = snap.plan
            if plan and len(snap.revealed_follow_up_timestamps) < len(plan.follow_ups):
                self._session.reveal_next_follow_up()
                self._on_follow_up_revealed()
                log.info("AgentLoop follow-up revealed  count=%d",
                         len(self._session.snapshot.revealed_follow_up_timestamps))
            parts = response.strip().split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                interjection_text = parts[1].strip()
            else:
                return
        elif response.strip().upper() == "NO":
            return
        else:
            interjection_text = response.strip()

        interjection = Interjection(text=interjection_text, trigger=trigger)
        self._session.add_interjection(interjection)
        self._last_interjection_at = datetime.now(timezone.utc)
        log.info("AgentLoop interjection  trigger=%s  text=%r", trigger, interjection.text[:100])
        self._on_interjection(interjection)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_agent_loop.py -v 2>&1 | tail -30
```

Expected: All PASS.

- [ ] **Step 5: Run the full test suite**

```bash
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests PASS (except `test_main.py` tests that exercise the feedback endpoint — those will be fixed in Task 6).

- [ ] **Step 6: Commit**

```bash
git add backend/agent/loop.py tests/test_agent_loop.py
git commit -m "feat: dynamic system prompt, REVEAL_NEXT_FOLLOWUP signal, follow-up timeline events"
```

---

## Task 6: Update main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Update `backend/main.py`**

Three changes: add `_on_follow_up_revealed` broadcast function, wire it into `AgentLoop`, update the feedback endpoint to use new `InterviewPlan` fields, fix the `plan_loaded` log line.

Find and replace each section:

**Replace the `_on_interjection` function and the section below it in `start_session` where `_agent_loop` is constructed:**

Old `_on_interjection`:
```python
async def _on_interjection(interjection: Interjection):
    await connection_manager.broadcast({
        "type": "interjection",
        "data": interjection.model_dump(mode="json"),
    })
```

New — add `_on_follow_up_revealed` right after:
```python
async def _on_interjection(interjection: Interjection):
    await connection_manager.broadcast({
        "type": "interjection",
        "data": interjection.model_dump(mode="json"),
    })


async def _on_follow_up_revealed():
    await connection_manager.broadcast({"type": "follow_up_revealed", "data": {}})
```

**Replace the `_agent_loop` construction in `start_session`:**

Old:
```python
    _agent_loop = AgentLoop(
        session=manager,
        llm=llm,
        min_interjection_gap_seconds=config.agent.min_seconds_between_interjections,
        on_interjection=lambda i: asyncio.ensure_future(_on_interjection(i)),
    )
```

New:
```python
    _agent_loop = AgentLoop(
        session=manager,
        llm=llm,
        min_interjection_gap_seconds=config.agent.min_seconds_between_interjections,
        on_interjection=lambda i: asyncio.ensure_future(_on_interjection(i)),
        on_follow_up_revealed=lambda: asyncio.ensure_future(_on_follow_up_revealed()),
    )
```

**Replace the log line in `load_question_endpoint`:**

Old:
```python
    log.info("Question loaded  problem=%s", plan.problem_statement[:80])
```

New:
```python
    log.info("Question loaded  problem=%s", plan.problem_markdown[:80])
```

**Replace the entire `generate_feedback` endpoint:**

Old:
```python
@app.post("/session/feedback")
async def generate_feedback():
    snap = manager.snapshot
    if not snap.plan:
        log.warning("Feedback requested but no plan loaded")
        raise HTTPException(status_code=400, detail="No interview plan loaded")
    log.info("Generating feedback  transcript_chunks=%d  deltas=%d", len(snap.transcript), len(snap.deltas))

    transcript_text = " ".join(c.text for c in snap.transcript)
    diffs_text = "\n".join(d.diff for d in snap.deltas)
    interjections_text = "\n".join(f"- {i.text}" for i in snap.interjections)
    rubric_text = "\n".join(f"{k}: {v}" for k, v in snap.plan.rubric.items())

    prompt = f"""You are reviewing a technical interview. Evaluate the candidate on each rubric dimension.

PROBLEM: {snap.plan.problem_statement}

RUBRIC:
{rubric_text}

TRANSCRIPT:
{transcript_text}

CODE CHANGES:
{diffs_text}

PROCTOR INTERJECTIONS (hints given):
{interjections_text}

Provide structured feedback: strengths, areas for improvement, and a rating (1-5) per rubric dimension."""

    feedback_text = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a senior technical interviewer providing constructive, honest feedback.",
    )
    log.info("Feedback generated  chars=%d", len(feedback_text))
    return {"feedback": feedback_text}
```

New:
```python
@app.post("/session/feedback")
async def generate_feedback():
    snap = manager.snapshot
    if not snap.plan:
        log.warning("Feedback requested but no plan loaded")
        raise HTTPException(status_code=400, detail="No interview plan loaded")
    log.info("Generating feedback  transcript_chunks=%d  deltas=%d", len(snap.transcript), len(snap.deltas))

    transcript_text = " ".join(c.text for c in snap.transcript)
    diffs_text = "\n".join(d.diff for d in snap.deltas)
    interjections_text = "\n".join(f"- {i.text}" for i in snap.interjections)

    prompt = f"""You are reviewing a technical interview. Evaluate the candidate on each rubric dimension.

PROBLEM:
{snap.plan.problem_markdown}

RUBRIC:
{snap.plan.rubric}

TRANSCRIPT:
{transcript_text}

CODE CHANGES:
{diffs_text}

PROCTOR INTERJECTIONS (hints given):
{interjections_text}

Provide structured feedback: strengths, areas for improvement, and a rating (1-5) per rubric dimension."""

    feedback_text = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a senior technical interviewer providing constructive, honest feedback.",
    )
    log.info("Feedback generated  chars=%d", len(feedback_text))
    return {"feedback": feedback_text}
```

- [ ] **Step 2: Run the full test suite**

```bash
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire follow-up reveal broadcast, update feedback endpoint for new model"
```

---

## Task 7: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/session.ts`

- [ ] **Step 1: Replace `frontend/src/types/session.ts`**

```typescript
export interface TranscriptChunk {
  text: string
  timestamp: string
  duration_seconds: number
}

export interface FileDelta {
  path: string
  diff: string
  timestamp: string
}

export interface Interjection {
  text: string
  timestamp: string
  trigger: 'speech_pause' | 'file_save'
}

export interface InterviewPlan {
  problem_markdown: string
  follow_ups: string[]
  agent_briefing: string
  rubric: string
  source_url: string | null
}

export interface SessionSnapshot {
  transcript: TranscriptChunk[]
  deltas: FileDelta[]
  interjections: Interjection[]
  plan: InterviewPlan | null
  started_at: string | null
  ended_at: string | null
  watch_path: string | null
  revealed_follow_up_timestamps: string[]
}

export type WSEventType =
  | 'plan_loaded'
  | 'session_started'
  | 'session_ended'
  | 'transcript_chunk'
  | 'file_delta'
  | 'interjection'
  | 'follow_up_revealed'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: Errors in `useSession.ts`, `QuestionPanel.tsx`, `Setup.tsx` (they reference old fields) — that's correct, they'll be fixed in upcoming tasks. No errors in `types/session.ts` itself.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/session.ts
git commit -m "feat: update frontend InterviewPlan type and add follow_up_revealed event"
```

---

## Task 8: Update useSession Hook

**Files:**
- Modify: `frontend/src/hooks/useSession.ts`

- [ ] **Step 1: Update `frontend/src/hooks/useSession.ts`**

Two changes: update `EMPTY_SNAPSHOT` to include `revealed_follow_up_timestamps`, and add the `follow_up_revealed` case to the message handler.

**Replace `EMPTY_SNAPSHOT`:**

Old:
```typescript
const EMPTY_SNAPSHOT: SessionSnapshot = {
  transcript: [],
  deltas: [],
  interjections: [],
  plan: null,
  started_at: null,
  ended_at: null,
  watch_path: null,
}
```

New:
```typescript
const EMPTY_SNAPSHOT: SessionSnapshot = {
  transcript: [],
  deltas: [],
  interjections: [],
  plan: null,
  started_at: null,
  ended_at: null,
  watch_path: null,
  revealed_follow_up_timestamps: [],
}
```

**Add `follow_up_revealed` case** inside the `switch (msg.type)` block, after the `'interjection'` case:

```typescript
          case 'follow_up_revealed':
            return {
              ...prev,
              revealed_follow_up_timestamps: [
                ...prev.revealed_follow_up_timestamps,
                new Date().toISOString(),
              ],
            }
```

- [ ] **Step 2: Verify TypeScript compiles (types only)**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble/frontend && npx tsc --noEmit 2>&1 | grep "useSession" | head -10
```

Expected: No errors in `useSession.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useSession.ts
git commit -m "feat: handle follow_up_revealed WS event in useSession"
```

---

## Task 9: Update QuestionPanel and Interview Screen

**Files:**
- Modify: `frontend/src/components/QuestionPanel.tsx`
- Modify: `frontend/src/screens/Interview.tsx`

- [ ] **Step 1: Replace `frontend/src/components/QuestionPanel.tsx`**

```tsx
import { MarkdownText } from './MarkdownText'
import type { InterviewPlan } from '../types/session'

interface Props {
  plan: InterviewPlan | null
  revealedCount: number
}

export default function QuestionPanel({ plan, revealedCount }: Props) {
  if (!plan) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.25)',
        fontSize: 14,
      }}>
        No question loaded.
      </div>
    )
  }

  return (
    <div style={{ padding: 28, overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}>
      <div style={{
        color: 'rgba(255,255,255,0.35)',
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '1.5px',
        fontWeight: 600,
        marginBottom: 12,
      }}>
        Problem
      </div>
      <MarkdownText style={{ color: 'rgba(255,255,255,0.95)', fontSize: 14 }}>
        {plan.problem_markdown}
      </MarkdownText>

      {plan.follow_ups.slice(0, revealedCount).map((followUp, i) => (
        <div key={i} style={{
          marginTop: 24,
          paddingLeft: 16,
          borderLeft: '2px solid rgba(96,208,255,0.3)',
        }}>
          <div style={{
            color: 'rgba(96,208,255,0.6)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            fontWeight: 600,
            marginBottom: 8,
          }}>
            Follow-up {i + 1}
          </div>
          <MarkdownText style={{ color: 'rgba(255,255,255,0.85)', fontSize: 14 }}>
            {followUp}
          </MarkdownText>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Update the `QuestionPanel` usage in `frontend/src/screens/Interview.tsx`**

Find the `QuestionPanel` call and add the `revealedCount` prop:

Old:
```tsx
          <QuestionPanel plan={snapshot.plan} />
```

New:
```tsx
          <QuestionPanel
            plan={snapshot.plan}
            revealedCount={snapshot.revealed_follow_up_timestamps.length}
          />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble/frontend && npx tsc --noEmit 2>&1 | grep -E "QuestionPanel|Interview" | head -10
```

Expected: No errors in these two files.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/QuestionPanel.tsx frontend/src/screens/Interview.tsx
git commit -m "feat: QuestionPanel renders markdown and shows revealed follow-ups"
```

---

## Task 10: Update Setup Screen QuestionPreview

**Files:**
- Modify: `frontend/src/screens/Setup.tsx`

- [ ] **Step 1: Update the `QuestionPreview` component in `Setup.tsx`**

Find the `QuestionPreview` function (lines ~95–180) and replace it entirely. The `SpoilerRow` component above it stays unchanged:

```tsx
function QuestionPreview({ plan }: { plan: InterviewPlan }) {
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const toggle = (key: string) => setOpen(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <div style={{
      background: 'rgba(96,208,255,0.05)',
      border: '1px solid rgba(96,208,255,0.18)',
      borderRadius: 12,
      padding: 16,
      marginBottom: 20,
    }}>
      <div style={{
        color: '#60d0ff',
        fontSize: 9,
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '1.5px',
        marginBottom: 10,
      }}>
        ✦ Question understood
      </div>
      <MarkdownText style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13 }}>
        {plan.problem_markdown}
      </MarkdownText>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
        {plan.follow_ups.length > 0 && (
          <SpoilerRow
            label="Follow-ups"
            count={plan.follow_ups.length}
            open={!!open.follow_ups}
            onToggle={() => toggle('follow_ups')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {plan.follow_ups.map((f, i) => (
                <div key={i} style={{
                  borderLeft: '2px solid rgba(96,208,255,0.3)',
                  paddingLeft: 10,
                }}>
                  <MarkdownText style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
                    {f}
                  </MarkdownText>
                </div>
              ))}
            </div>
          </SpoilerRow>
        )}
        <SpoilerRow
          label="Rubric"
          count={1}
          open={!!open.rubric}
          onToggle={() => toggle('rubric')}
        >
          <MarkdownText style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
            {plan.rubric}
          </MarkdownText>
        </SpoilerRow>
        <SpoilerRow
          label="Agent Brief"
          count={1}
          open={!!open.briefing}
          onToggle={() => toggle('briefing')}
        >
          <MarkdownText style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
            {plan.agent_briefing}
          </MarkdownText>
        </SpoilerRow>
      </div>
    </div>
  )
}
```

Also add the `MarkdownText` import at the top of `Setup.tsx`. The current imports are likely:
```tsx
import type { ReactNode } from 'react'
// ... other imports
```

Add after the existing component imports:
```tsx
import { MarkdownText } from '../components/MarkdownText'
```

Also remove the import of `HintStep` from `Setup.tsx` if present (check the import line for `'../types/session'` and remove `HintStep`).

- [ ] **Step 2: Verify TypeScript compiles with zero errors**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: Zero TypeScript errors.

- [ ] **Step 3: Run the full backend test suite one final time**

```bash
cd /Users/Konstantin/projects/proctor_and_ramble && python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/screens/Setup.tsx
git commit -m "feat: update Setup QuestionPreview for new InterviewPlan shape"
```
