# Proctor & Ramble V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local AI interviewer that watches speech + code in real time, intervenes with Socratic nudges, and produces structured post-interview feedback.

**Architecture:** Python backend (FastAPI + WebSocket) serves a React/TypeScript frontend over localhost. The backend runs three concurrent systems: an STT engine that streams mic audio, a file watcher that diffs code changes, and an agent loop that decides when to intervene. All engines (STT, LLM) are swappable via abstract base classes.

**Tech Stack:** Python 3.11+, FastAPI, WebSocket, Pydantic, mlx-whisper, openai SDK, watchdog, sounddevice, httpx / React 18, TypeScript, Vite

---

## File Map

```
backend/
  __init__.py
  config.py                  # loads config.yaml + .env → AppConfig
  main.py                    # FastAPI app, WebSocket hub, REST endpoints
  engines/
    __init__.py
    llm_base.py              # BaseLLMClient ABC
    openai_client.py         # OpenAIClient impl
    stt_base.py              # BaseSTTEngine ABC
    mlx_whisper.py           # MLXWhisperEngine impl
  session/
    __init__.py
    models.py                # Pydantic: TranscriptChunk, FileDelta, Interjection, InterviewPlan, SessionSnapshot
    manager.py               # SessionManager (single source of truth)
  question/
    __init__.py
    loader.py                # URL fetch → LLM extract + enrich → InterviewPlan
  watcher/
    __init__.py
    file_watcher.py          # watchdog wrapper, emits FileDelta on save
  agent/
    __init__.py
    loop.py                  # trigger listener + LLM judge + interjection emitter
tests/
  __init__.py
  test_models.py
  test_config.py
  test_session_manager.py
  test_openai_client.py
  test_question_loader.py
  test_file_watcher.py
  test_agent_loop.py
  test_main.py
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    types/
      session.ts             # Shared TS types for WS events + session state
    hooks/
      useSession.ts          # WebSocket connection + session state
    screens/
      Setup.tsx
      Interview.tsx
      Feedback.tsx
    components/
      Timer.tsx
      QuestionPanel.tsx
      ProctorPanel.tsx
      ExportButton.tsx
```

---

## Phase 1 — Backend Core

### Task 1: Python project scaffold

**Files:**
- Create: `backend/__init__.py`, `backend/engines/__init__.py`, `backend/session/__init__.py`, `backend/question/__init__.py`, `backend/watcher/__init__.py`, `backend/agent/__init__.py`
- Create: `tests/__init__.py`
- Create: `pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "proctor_and_ramble"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "openai>=1.30",
    "httpx>=0.27",
    "watchdog>=4.0",
    "sounddevice>=0.4",
    "numpy>=1.26",
    "mlx-whisper>=0.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create all `__init__.py` files and install deps**

```bash
touch backend/__init__.py backend/engines/__init__.py backend/session/__init__.py \
      backend/question/__init__.py backend/watcher/__init__.py backend/agent/__init__.py \
      tests/__init__.py
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 3: Verify pytest runs with no tests**

```bash
pytest
```
Expected: `no tests ran` or `0 passed`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml backend/ tests/__init__.py
git commit -m "feat: python project scaffold with deps and pytest"
```

---

### Task 2: Session models

**Files:**
- Create: `backend/session/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement models**

```python
# backend/session/models.py
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/session/models.py tests/test_models.py
git commit -m "feat: pydantic session models"
```

---

### Task 3: Config loader

**Files:**
- Create: `backend/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
import yaml
from pathlib import Path
from backend.config import load_config, AppConfig

def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "stt": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-mlx", "speech_pause_threshold_seconds": 3},
        "llm": {"provider": "openai", "model": "gpt-4o"},
        "agent": {"min_seconds_between_interjections": 30, "context_transcript_chunks": 20, "context_recent_deltas": 5},
        "server": {"host": "127.0.0.1", "port": 8000},
        "frontend": {"port": 5173},
    }))
    config = load_config(str(cfg_file))
    assert isinstance(config, AppConfig)
    assert config.stt.engine == "mlx_whisper"
    assert config.llm.model == "gpt-4o"
    assert config.agent.min_seconds_between_interjections == 30
    assert config.server.port == 8000

def test_load_config_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "stt": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-mlx"},
        "llm": {"provider": "openai", "model": "gpt-4o"},
    }))
    config = load_config(str(cfg_file))
    assert config.stt.speech_pause_threshold_seconds == 3.0
    assert config.agent.min_seconds_between_interjections == 30
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement config loader**

```python
# backend/config.py
import yaml
from pydantic import BaseModel


class STTConfig(BaseModel):
    engine: str
    model: str
    speech_pause_threshold_seconds: float = 3.0


class LLMConfig(BaseModel):
    provider: str
    model: str


class AgentConfig(BaseModel):
    min_seconds_between_interjections: int = 30
    context_transcript_chunks: int = 20
    context_recent_deltas: int = 5


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class FrontendConfig(BaseModel):
    port: int = 5173


class AppConfig(BaseModel):
    stt: STTConfig
    llm: LLMConfig
    agent: AgentConfig = AgentConfig()
    server: ServerConfig = ServerConfig()
    frontend: FrontendConfig = FrontendConfig()


def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/test_config.py
git commit -m "feat: config loader with pydantic validation"
```

---

### Task 4: Session manager

**Files:**
- Create: `backend/session/manager.py`
- Create: `tests/test_session_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session_manager.py
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


def test_recent_transcript_chunks(manager):
    manager.start(watch_path="/foo")
    for i in range(25):
        manager.add_transcript_chunk(TranscriptChunk(text=f"chunk {i}", duration_seconds=1.0))
    recent = manager.recent_transcript_chunks(n=20)
    assert len(recent) == 20
    assert recent[-1].text == "chunk 24"


def test_recent_deltas(manager):
    manager.start(watch_path="/foo")
    for i in range(10):
        manager.add_file_delta(FileDelta(path="/foo", diff=f"+ line {i}"))
    recent = manager.recent_deltas(n=5)
    assert len(recent) == 5
    assert recent[-1].diff == "+ line 9"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_session_manager.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement session manager**

```python
# backend/session/manager.py
from datetime import datetime
from backend.session.models import (
    TranscriptChunk, FileDelta, Interjection,
    InterviewPlan, SessionSnapshot,
)


class SessionManager:
    def __init__(self):
        self.snapshot = SessionSnapshot()

    def start(self, watch_path: str) -> None:
        self.snapshot = SessionSnapshot(
            started_at=datetime.utcnow(),
            watch_path=watch_path,
        )

    def end(self) -> None:
        self.snapshot.ended_at = datetime.utcnow()

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_session_manager.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/session/manager.py tests/test_session_manager.py
git commit -m "feat: session manager as single source of truth"
```

---

### Task 5: LLM base class + OpenAI impl

**Files:**
- Create: `backend/engines/llm_base.py`
- Create: `backend/engines/openai_client.py`
- Create: `tests/test_openai_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_openai_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.engines.llm_base import BaseLLMClient
from backend.engines.openai_client import OpenAIClient


def test_openai_client_is_base():
    assert issubclass(OpenAIClient, BaseLLMClient)


@pytest.mark.asyncio
async def test_complete_returns_string():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hello from mock"

    with patch("backend.engines.openai_client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        client = OpenAIClient(model="gpt-4o", api_key="sk-test")
        result = await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are helpful.",
        )

    assert result == "Hello from mock"


@pytest.mark.asyncio
async def test_complete_includes_system_prompt():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "ok"

    with patch("backend.engines.openai_client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        client = OpenAIClient(model="gpt-4o", api_key="sk-test")
        await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are a proctor.",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages_sent = call_args.kwargs["messages"]

    assert messages_sent[0] == {"role": "system", "content": "You are a proctor."}
    assert messages_sent[1] == {"role": "user", "content": "hi"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_openai_client.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement LLM base class**

```python
# backend/engines/llm_base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        """Send messages and return the full completion."""
        ...

    @abstractmethod
    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        """Send messages and stream the completion token by token."""
        ...
```

- [ ] **Step 4: Implement OpenAI client**

```python
# backend/engines/openai_client.py
from typing import AsyncIterator
from openai import AsyncOpenAI
from backend.engines.llm_base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    def _build_messages(self, messages: list[dict], system_prompt: str) -> list[dict]:
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        return all_messages

    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(messages, system_prompt),
        )
        return response.choices[0].message.content

    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(messages, system_prompt),
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_openai_client.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/llm_base.py backend/engines/openai_client.py tests/test_openai_client.py
git commit -m "feat: LLM base class + OpenAI client impl"
```

---

### Task 6: Question loader

**Files:**
- Create: `backend/question/loader.py`
- Create: `tests/test_question_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_question_loader.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.question.loader import load_question
from backend.session.models import InterviewPlan


MOCK_LLM_RESPONSE = json.dumps({
    "problem_statement": "Given an array of integers, return indices of the two numbers that add up to target.",
    "constraints": ["2 <= nums.length <= 10^4", "Each input has exactly one solution"],
    "hints": [
        {"level": 1, "text": "Think about what complement you need for each number."},
        {"level": 2, "text": "A hash map can give O(1) lookups."},
    ],
    "expected_approaches": ["Brute force O(n²)", "Hash map O(n)"],
    "follow_up_questions": ["What if the array is sorted?", "What if there are multiple valid answers?"],
    "rubric": {
        "correctness": "Returns correct indices for all test cases",
        "efficiency": "Achieves O(n) time complexity",
        "communication": "Explains reasoning while coding",
        "edge_cases": "Handles negative numbers and duplicates",
    },
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
    assert "two numbers" in plan.problem_statement.lower() or "indices" in plan.problem_statement.lower()
    assert len(plan.hints) == 2
    assert plan.hints[0].level == 1
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_question_loader.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement question loader**

```python
# backend/question/loader.py
import json
from html.parser import HTMLParser
import httpx
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import InterviewPlan


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
Extract the interview question from the page content below and enrich it into a \
full interview plan. Return ONLY valid JSON with exactly these fields:

{
  "problem_statement": "...",
  "constraints": ["...", "..."],
  "hints": [{"level": 1, "text": "subtle hint"}, {"level": 2, "text": "more direct"}],
  "expected_approaches": ["...", "..."],
  "follow_up_questions": ["...", "..."],
  "rubric": {
    "correctness": "...",
    "efficiency": "...",
    "communication": "...",
    "edge_cases": "..."
  }
}

Page content:
"""

_SYSTEM_PROMPT = (
    "You are an expert technical interviewer preparing a structured interview plan. "
    "Return only valid JSON, no markdown fences."
)


async def load_question(url: str, llm: BaseLLMClient) -> InterviewPlan:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    page_text = extractor.text[:8000]

    raw = await llm.complete(
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + page_text}],
        system_prompt=_SYSTEM_PROMPT,
    )

    data = json.loads(raw.strip())
    return InterviewPlan(**data, source_url=url)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_question_loader.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/question/loader.py tests/test_question_loader.py
git commit -m "feat: question loader — URL fetch + LLM enrichment to InterviewPlan"
```

---

## Phase 2 — Backend Real-Time

### Task 7: STT base class + mlx-whisper impl

**Files:**
- Create: `backend/engines/stt_base.py`
- Create: `backend/engines/mlx_whisper.py`
- Create: `tests/test_stt_base.py`

Note: mlx-whisper uses real audio hardware; tests cover the interface contract and a mock subclass only.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stt_base.py
import pytest
from backend.engines.stt_base import BaseSTTEngine
from backend.session.models import TranscriptChunk


class MockSTTEngine(BaseSTTEngine):
    def __init__(self):
        self._transcript_cb = None
        self._pause_cb = None
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def set_on_transcript(self, callback):
        self._transcript_cb = callback

    def set_on_speech_pause(self, callback):
        self._pause_cb = callback

    async def simulate_transcript(self, text: str):
        if self._transcript_cb:
            await self._transcript_cb(TranscriptChunk(text=text, duration_seconds=1.0))

    async def simulate_pause(self):
        if self._pause_cb:
            await self._pause_cb()


@pytest.mark.asyncio
async def test_mock_stt_fires_transcript_callback():
    received = []
    engine = MockSTTEngine()
    engine.set_on_transcript(lambda chunk: received.append(chunk) or __import__('asyncio').sleep(0))

    async def cb(chunk):
        received.append(chunk)

    engine.set_on_transcript(cb)
    await engine.simulate_transcript("hello")
    assert len(received) == 1
    assert received[0].text == "hello"


@pytest.mark.asyncio
async def test_mock_stt_fires_pause_callback():
    paused = []
    engine = MockSTTEngine()

    async def on_pause():
        paused.append(True)

    engine.set_on_speech_pause(on_pause)
    await engine.simulate_pause()
    assert paused == [True]


def test_mock_stt_lifecycle():
    engine = MockSTTEngine()
    assert not engine.started
    engine.start()
    assert engine.started
    engine.stop()
    assert not engine.started
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stt_base.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement STT base class**

```python
# backend/engines/stt_base.py
from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from backend.session.models import TranscriptChunk


class BaseSTTEngine(ABC):
    @abstractmethod
    def start(self) -> None:
        """Begin audio capture and transcription."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture and release resources."""
        ...

    @abstractmethod
    def set_on_transcript(
        self, callback: Callable[[TranscriptChunk], Awaitable[None]]
    ) -> None:
        """Register callback fired on each transcribed segment."""
        ...

    @abstractmethod
    def set_on_speech_pause(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register callback fired when silence exceeds the threshold."""
        ...
```

- [ ] **Step 4: Implement mlx-whisper engine**

```python
# backend/engines/mlx_whisper.py
import asyncio
import threading
from typing import Callable, Awaitable
import numpy as np
import sounddevice as sd
import mlx_whisper
from backend.engines.stt_base import BaseSTTEngine
from backend.session.models import TranscriptChunk

_SAMPLE_RATE = 16000
_BLOCK_SIZE = 1600  # 100ms
_SPEECH_THRESHOLD = 0.01  # RMS level above which we consider speech


class MLXWhisperEngine(BaseSTTEngine):
    def __init__(self, model: str, pause_threshold_seconds: float = 3.0):
        self._model = model
        self._pause_threshold = pause_threshold_seconds
        self._on_transcript: Callable[[TranscriptChunk], Awaitable[None]] | None = None
        self._on_speech_pause: Callable[[], Awaitable[None]] | None = None
        self._buffer: list[float] = []
        self._silence_duration = 0.0
        self._stream: sd.InputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def set_on_transcript(self, callback: Callable[[TranscriptChunk], Awaitable[None]]) -> None:
        self._on_transcript = callback

    def set_on_speech_pause(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._on_speech_pause = callback

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _audio_callback(self, indata, frames, time, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        with self._lock:
            if rms > _SPEECH_THRESHOLD:
                self._buffer.extend(indata[:, 0].tolist())
                self._silence_duration = 0.0
            else:
                self._silence_duration += frames / _SAMPLE_RATE
                if self._silence_duration >= self._pause_threshold and self._buffer:
                    audio = np.array(self._buffer, dtype=np.float32)
                    self._buffer = []
                    self._silence_duration = 0.0
                    asyncio.run_coroutine_threadsafe(
                        self._transcribe_and_notify(audio), self._loop
                    )

    async def _transcribe_and_notify(self, audio: np.ndarray) -> None:
        result = mlx_whisper.transcribe(audio, path_or_hf_repo=self._model)
        text = result.get("text", "").strip()
        if text and self._on_transcript:
            chunk = TranscriptChunk(
                text=text, duration_seconds=len(audio) / _SAMPLE_RATE
            )
            await self._on_transcript(chunk)
        if self._on_speech_pause:
            await self._on_speech_pause()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_stt_base.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stt_base.py backend/engines/mlx_whisper.py tests/test_stt_base.py
git commit -m "feat: STT base class + mlx-whisper engine impl"
```

---

### Task 8: File watcher

**Files:**
- Create: `backend/watcher/file_watcher.py`
- Create: `tests/test_file_watcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_file_watcher.py
import asyncio
import pytest
from pathlib import Path
from backend.watcher.file_watcher import FileWatcher
from backend.session.models import FileDelta


@pytest.mark.asyncio
async def test_file_watcher_emits_delta_on_save(tmp_path):
    target = tmp_path / "solution.py"
    target.write_text("x = 1\n")

    received: list[FileDelta] = []

    async def on_delta(delta: FileDelta):
        received.append(delta)

    watcher = FileWatcher(path=str(target), on_delta=on_delta)
    watcher.start()

    await asyncio.sleep(0.5)
    target.write_text("x = 1\ny = 2\n")
    await asyncio.sleep(1.5)

    watcher.stop()
    assert len(received) == 1
    assert "+ y = 2" in received[0].diff
    assert received[0].path == str(target)


@pytest.mark.asyncio
async def test_file_watcher_tracks_multiple_saves(tmp_path):
    target = tmp_path / "sol.py"
    target.write_text("pass\n")

    received: list[FileDelta] = []

    async def on_delta(delta: FileDelta):
        received.append(delta)

    watcher = FileWatcher(path=str(target), on_delta=on_delta)
    watcher.start()

    await asyncio.sleep(0.3)
    target.write_text("x = 1\n")
    await asyncio.sleep(1.2)
    target.write_text("x = 1\ny = 2\n")
    await asyncio.sleep(1.2)

    watcher.stop()
    assert len(received) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_file_watcher.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement file watcher**

```python
# backend/watcher/file_watcher.py
import asyncio
import difflib
from pathlib import Path
from typing import Callable, Awaitable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from backend.session.models import FileDelta


class _Handler(FileSystemEventHandler):
    def __init__(self, target: str, callback):
        self._target = str(Path(target).resolve())
        self._callback = callback

    def on_modified(self, event):
        if not event.is_directory and str(Path(event.src_path).resolve()) == self._target:
            self._callback()


class FileWatcher:
    def __init__(self, path: str, on_delta: Callable[[FileDelta], Awaitable[None]]):
        self._path = str(Path(path).resolve())
        self._on_delta = on_delta
        self._last_content: str = self._read()
        self._observer = Observer()
        self._loop: asyncio.AbstractEventLoop | None = None

    def _read(self) -> str:
        try:
            return Path(self._path).read_text()
        except FileNotFoundError:
            return ""

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        handler = _Handler(self._path, self._on_file_changed)
        watch_dir = str(Path(self._path).parent)
        self._observer.schedule(handler, watch_dir, recursive=False)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()

    def _on_file_changed(self) -> None:
        new_content = self._read()
        diff_lines = list(
            difflib.unified_diff(
                self._last_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
            )
        )
        if diff_lines:
            diff = "".join(diff_lines)
            self._last_content = new_content
            delta = FileDelta(path=self._path, diff=diff)
            asyncio.run_coroutine_threadsafe(self._on_delta(delta), self._loop)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_file_watcher.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/watcher/file_watcher.py tests/test_file_watcher.py
git commit -m "feat: file watcher with unified diff emission"
```

---

### Task 9: Agent loop

**Files:**
- Create: `backend/agent/loop.py`
- Create: `tests/test_agent_loop.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_loop.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent_loop.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement agent loop**

```python
# backend/agent/loop.py
from datetime import datetime, timedelta
from typing import Callable
from backend.session.manager import SessionManager
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import Interjection

_SYSTEM_PROMPT = """\
You are a technical interview proctor watching a candidate solve a problem in real time.
You see their speech transcript and code changes.

Your role: provide short, Socratic nudges when the candidate needs guidance. Never give away the answer.

Rules:
- If the candidate is actively making progress or speaking confidently: respond with exactly "NO"
- If they seem stuck, confused, or could benefit from a nudge: provide 1-2 sentences of guidance
- Be encouraging, directional, never patronizing
- Never solve the problem for them

Respond with either "NO" or the interjection text. No preamble."""


class AgentLoop:
    def __init__(
        self,
        session: SessionManager,
        llm: BaseLLMClient,
        min_interjection_gap_seconds: int,
        on_interjection: Callable[[Interjection], None],
    ):
        self._session = session
        self._llm = llm
        self._gap = min_interjection_gap_seconds
        self._on_interjection = on_interjection
        self._last_interjection_at: datetime | None = None

    async def on_speech_pause(self) -> None:
        await self._maybe_intervene(trigger="speech_pause")

    async def on_file_save(self) -> None:
        await self._maybe_intervene(trigger="file_save")

    def _cooldown_active(self) -> bool:
        if self._last_interjection_at is None:
            return False
        elapsed = (datetime.utcnow() - self._last_interjection_at).total_seconds()
        return elapsed < self._gap

    def _build_context(self) -> str:
        snap = self._session.snapshot
        plan = snap.plan
        chunks = self._session.recent_transcript_chunks(n=20)
        deltas = self._session.recent_deltas(n=5)

        parts = []
        if plan:
            parts.append(f"PROBLEM: {plan.problem_statement}")
        if chunks:
            transcript = " ".join(c.text for c in chunks)
            parts.append(f"RECENT SPEECH: {transcript}")
        if deltas:
            diffs = "\n".join(d.diff for d in deltas)
            parts.append(f"RECENT CODE CHANGES:\n{diffs}")
        elapsed = ""
        if snap.started_at:
            secs = int((datetime.utcnow() - snap.started_at).total_seconds())
            elapsed = f"{secs // 60}m {secs % 60}s"
            parts.append(f"TIME ELAPSED: {elapsed}")

        return "\n\n".join(parts)

    async def _maybe_intervene(self, trigger: str) -> None:
        if self._cooldown_active():
            return

        context = self._build_context()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": context}],
            system_prompt=_SYSTEM_PROMPT,
        )

        if response.strip().upper() == "NO":
            return

        interjection = Interjection(text=response.strip(), trigger=trigger)
        self._session.add_interjection(interjection)
        self._last_interjection_at = datetime.utcnow()
        self._on_interjection(interjection)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent_loop.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/agent/loop.py tests/test_agent_loop.py
git commit -m "feat: agent loop with cooldown, LLM judge, and trigger handling"
```

---

### Task 10: FastAPI app + WebSocket hub

**Files:**
- Create: `backend/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_main.py
import pytest
import json
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from fastapi.testclient import TestClient
from backend.main import app, manager as session_manager


@pytest.fixture(autouse=True)
def reset_session():
    from backend.main import connection_manager
    connection_manager.active_connections.clear()
    yield


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_question_missing_url():
    response = client.post("/question/load", json={})
    assert response.status_code == 422


def test_start_session_missing_watch_path():
    response = client.post("/session/start", json={})
    assert response.status_code == 422


def test_start_session():
    response = client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_end_session():
    client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    response = client.post("/session/end")
    assert response.status_code == 200
    assert response.json()["status"] == "ended"


def test_get_snapshot():
    client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    response = client.get("/session/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert "interjections" in data
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement FastAPI app**

```python
# backend/main.py
import asyncio
import os
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.config import load_config
from backend.session.manager import SessionManager
from backend.session.models import Interjection
from backend.engines.openai_client import OpenAIClient
from backend.question.loader import load_question
from backend.watcher.file_watcher import FileWatcher
from backend.agent.loop import AgentLoop

load_dotenv()

config = load_config()
manager = SessionManager()
llm = OpenAIClient(model=config.llm.model, api_key=os.environ.get("OPENAI_API_KEY"))

_file_watcher: FileWatcher | None = None
_agent_loop: AgentLoop | None = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


connection_manager = ConnectionManager()


async def _on_interjection(interjection: Interjection):
    await connection_manager.broadcast({
        "type": "interjection",
        "data": interjection.model_dump(mode="json"),
    })


app = FastAPI(title="Proctor & Ramble")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


class LoadQuestionRequest(BaseModel):
    url: str


@app.post("/question/load")
async def load_question_endpoint(req: LoadQuestionRequest):
    plan = await load_question(req.url, llm)
    manager.set_plan(plan)
    await connection_manager.broadcast({
        "type": "plan_loaded",
        "data": plan.model_dump(mode="json"),
    })
    return {"status": "ok", "plan": plan.model_dump(mode="json")}


class StartSessionRequest(BaseModel):
    watch_path: str


@app.post("/session/start")
async def start_session(req: StartSessionRequest):
    global _file_watcher, _agent_loop

    manager.start(watch_path=req.watch_path)

    _agent_loop = AgentLoop(
        session=manager,
        llm=llm,
        min_interjection_gap_seconds=config.agent.min_seconds_between_interjections,
        on_interjection=lambda i: asyncio.ensure_future(_on_interjection(i)),
    )

    _file_watcher = FileWatcher(
        path=req.watch_path,
        on_delta=_handle_file_delta,
    )
    _file_watcher.start()

    await connection_manager.broadcast({"type": "session_started", "data": {}})
    return {"status": "started"}


async def _handle_file_delta(delta):
    manager.add_file_delta(delta)
    await connection_manager.broadcast({
        "type": "file_delta",
        "data": delta.model_dump(mode="json"),
    })
    if _agent_loop:
        await _agent_loop.on_file_save()


@app.post("/session/end")
async def end_session():
    global _file_watcher
    if _file_watcher:
        _file_watcher.stop()
        _file_watcher = None
    manager.end()
    await connection_manager.broadcast({"type": "session_ended", "data": {}})
    return {"status": "ended"}


@app.get("/session/snapshot")
async def get_snapshot():
    return manager.snapshot.model_dump(mode="json")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Run the full backend test suite**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_main.py
git commit -m "feat: FastAPI app with WebSocket hub and REST endpoints"
```

---

## Phase 3 — Frontend

### Task 11: Frontend scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: Scaffold with Vite**

```bash
cd frontend
npm create vite@latest . -- --template react-ts --yes
npm install
```

- [ ] **Step 2: Update vite.config.ts for backend proxy**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/question': 'http://127.0.0.1:8000',
      '/session': 'http://127.0.0.1:8000',
    },
  },
})
```

- [ ] **Step 3: Replace App.tsx with screen router**

```tsx
// frontend/src/App.tsx
import { useState } from 'react'
import Setup from './screens/Setup'
import Interview from './screens/Interview'
import Feedback from './screens/Feedback'

export type Screen = 'setup' | 'interview' | 'feedback'

export default function App() {
  const [screen, setScreen] = useState<Screen>('setup')

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {screen === 'setup' && <Setup onStart={() => setScreen('interview')} />}
      {screen === 'interview' && <Interview onEnd={() => setScreen('feedback')} />}
      {screen === 'feedback' && <Feedback onReset={() => setScreen('setup')} />}
    </div>
  )
}
```

- [ ] **Step 4: Verify frontend builds**

```bash
npm run build
```
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: Vite + React + TypeScript frontend scaffold"
```

---

### Task 12: WebSocket types + useSession hook

**Files:**
- Create: `frontend/src/types/session.ts`
- Create: `frontend/src/hooks/useSession.ts`

- [ ] **Step 1: Create shared session types**

```typescript
// frontend/src/types/session.ts
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

export interface HintStep {
  level: number
  text: string
}

export interface InterviewPlan {
  problem_statement: string
  constraints: string[]
  hints: HintStep[]
  expected_approaches: string[]
  follow_up_questions: string[]
  rubric: Record<string, string>
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
}

export type WSEventType =
  | 'plan_loaded'
  | 'session_started'
  | 'session_ended'
  | 'transcript_chunk'
  | 'file_delta'
  | 'interjection'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}
```

- [ ] **Step 2: Create useSession hook**

```typescript
// frontend/src/hooks/useSession.ts
import { useEffect, useRef, useState, useCallback } from 'react'
import type { SessionSnapshot, WSEvent, Interjection, InterviewPlan } from '../types/session'

const WS_URL = 'ws://127.0.0.1:8000/ws'

const EMPTY_SNAPSHOT: SessionSnapshot = {
  transcript: [],
  deltas: [],
  interjections: [],
  plan: null,
  started_at: null,
  ended_at: null,
  watch_path: null,
}

export function useSession() {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>(EMPTY_SNAPSHOT)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)

    ws.onmessage = (event) => {
      const msg: WSEvent = JSON.parse(event.data)
      setSnapshot((prev) => {
        switch (msg.type) {
          case 'plan_loaded':
            return { ...prev, plan: msg.data as unknown as InterviewPlan }
          case 'session_started':
            return { ...prev, started_at: new Date().toISOString() }
          case 'session_ended':
            return { ...prev, ended_at: new Date().toISOString() }
          case 'interjection':
            return {
              ...prev,
              interjections: [msg.data as unknown as Interjection, ...prev.interjections],
            }
          default:
            return prev
        }
      })
    }

    return () => ws.close()
  }, [])

  const loadQuestion = useCallback(async (url: string) => {
    const res = await fetch('/question/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!res.ok) throw new Error('Failed to load question')
    return res.json()
  }, [])

  const startSession = useCallback(async (watchPath: string) => {
    const res = await fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watch_path: watchPath }),
    })
    if (!res.ok) throw new Error('Failed to start session')
  }, [])

  const endSession = useCallback(async () => {
    await fetch('/session/end', { method: 'POST' })
  }, [])

  const fetchSnapshot = useCallback(async () => {
    const res = await fetch('/session/snapshot')
    const data: SessionSnapshot = await res.json()
    setSnapshot(data)
    return data
  }, [])

  return { snapshot, connected, loadQuestion, startSession, endSession, fetchSnapshot }
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/src/types/ frontend/src/hooks/
git commit -m "feat: WebSocket session types and useSession hook"
```

---

### Task 13: Setup screen

**Files:**
- Create: `frontend/src/screens/Setup.tsx`

- [ ] **Step 1: Implement Setup screen**

```tsx
// frontend/src/screens/Setup.tsx
import { useState } from 'react'
import { useSession } from '../hooks/useSession'

interface Props {
  onStart: () => void
}

export default function Setup({ onStart }: Props) {
  const [url, setUrl] = useState('')
  const [watchPath, setWatchPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [planLoaded, setPlanLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { loadQuestion, startSession } = useSession()

  const handleLoadQuestion = async () => {
    if (!url) return
    setLoading(true)
    setError(null)
    try {
      await loadQuestion(url)
      setPlanLoaded(true)
    } catch (e) {
      setError('Failed to load question. Check the URL and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!watchPath) return
    setLoading(true)
    try {
      await startSession(watchPath)
      onStart()
    } catch (e) {
      setError('Failed to start session.')
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 560, margin: '80px auto', padding: '0 24px' }}>
      <h1 style={{ marginBottom: 8 }}>Proctor & Ramble</h1>
      <p style={{ color: '#666', marginBottom: 40 }}>AI-powered technical interview proctor</p>

      <section style={{ marginBottom: 32 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
          Interview question URL
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://leetcode.com/problems/two-sum/"
            style={{ flex: 1, padding: '8px 12px', fontSize: 14, border: '1px solid #ccc', borderRadius: 6 }}
            onKeyDown={(e) => e.key === 'Enter' && handleLoadQuestion()}
          />
          <button
            onClick={handleLoadQuestion}
            disabled={!url || loading}
            style={{ padding: '8px 16px', cursor: 'pointer', borderRadius: 6, border: 'none', background: '#0070f3', color: '#fff', fontWeight: 600 }}
          >
            {loading ? '...' : 'Load'}
          </button>
        </div>
        {planLoaded && <p style={{ color: '#16a34a', marginTop: 8, fontSize: 13 }}>✓ Question loaded</p>}
      </section>

      <section style={{ marginBottom: 32 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
          Watch path (file or folder)
        </label>
        <input
          type="text"
          value={watchPath}
          onChange={(e) => setWatchPath(e.target.value)}
          placeholder="/Users/you/projects/solution.py"
          style={{ width: '100%', padding: '8px 12px', fontSize: 14, border: '1px solid #ccc', borderRadius: 6, boxSizing: 'border-box' }}
        />
      </section>

      {error && <p style={{ color: '#dc2626', marginBottom: 16, fontSize: 13 }}>{error}</p>}

      <button
        onClick={handleStart}
        disabled={!planLoaded || !watchPath || loading}
        style={{
          width: '100%', padding: '12px', fontSize: 16, fontWeight: 700,
          background: planLoaded && watchPath ? '#111' : '#e5e7eb',
          color: planLoaded && watchPath ? '#fff' : '#9ca3af',
          border: 'none', borderRadius: 8, cursor: planLoaded && watchPath ? 'pointer' : 'not-allowed',
        }}
      >
        Start Interview
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/screens/Setup.tsx
git commit -m "feat: Setup screen with URL input and watch path"
```

---

### Task 14: Interview screen components

**Files:**
- Create: `frontend/src/components/Timer.tsx`
- Create: `frontend/src/components/QuestionPanel.tsx`
- Create: `frontend/src/components/ProctorPanel.tsx`

- [ ] **Step 1: Implement Timer**

```tsx
// frontend/src/components/Timer.tsx
import { useEffect, useState } from 'react'

interface Props {
  startedAt: string | null
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function Timer({ startedAt }: Props) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt).getTime()
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [startedAt])

  return (
    <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600, fontSize: 18 }}>
      ⏱ {formatTime(elapsed)}
    </span>
  )
}
```

- [ ] **Step 2: Implement QuestionPanel**

```tsx
// frontend/src/components/QuestionPanel.tsx
import type { InterviewPlan } from '../types/session'

interface Props {
  plan: InterviewPlan | null
}

export default function QuestionPanel({ plan }: Props) {
  if (!plan) {
    return (
      <div style={{ padding: 24, color: '#9ca3af' }}>
        No question loaded.
      </div>
    )
  }

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <h2 style={{ marginTop: 0, fontSize: 18 }}>Problem</h2>
      <p style={{ lineHeight: 1.6 }}>{plan.problem_statement}</p>

      {plan.constraints.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, color: '#6b7280', marginTop: 24 }}>CONSTRAINTS</h3>
          <ul style={{ paddingLeft: 20, lineHeight: 1.8 }}>
            {plan.constraints.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Implement ProctorPanel**

```tsx
// frontend/src/components/ProctorPanel.tsx
import type { Interjection } from '../types/session'

interface Props {
  interjections: Interjection[]
}

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  return `${Math.floor(diff / 60)}m ago`
}

export default function ProctorPanel({ interjections }: Props) {
  if (interjections.length === 0) {
    return (
      <div style={{ padding: 24, color: '#9ca3af', fontSize: 14 }}>
        Proctor is watching...
      </div>
    )
  }

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <h2 style={{ marginTop: 0, fontSize: 18 }}>Proctor</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {interjections.map((item, i) => (
          <div
            key={i}
            style={{
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '12px 16px',
            }}
          >
            <p style={{ margin: 0, lineHeight: 1.6 }}>{item.text}</p>
            <span style={{ fontSize: 11, color: '#9ca3af', marginTop: 6, display: 'block' }}>
              {timeAgo(item.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/src/components/
git commit -m "feat: Timer, QuestionPanel, and ProctorPanel components"
```

---

### Task 15: Interview screen

**Files:**
- Create: `frontend/src/screens/Interview.tsx`

- [ ] **Step 1: Implement Interview screen**

```tsx
// frontend/src/screens/Interview.tsx
import { useEffect } from 'react'
import Timer from '../components/Timer'
import QuestionPanel from '../components/QuestionPanel'
import ProctorPanel from '../components/ProctorPanel'
import { useSession } from '../hooks/useSession'

interface Props {
  onEnd: () => void
}

export default function Interview({ onEnd }: Props) {
  const { snapshot, connected, endSession, fetchSnapshot } = useSession()

  // Populate plan + session state that was set up during Setup screen
  useEffect(() => { fetchSnapshot() }, [])

  const handleEnd = async () => {
    await endSession()
    onEnd()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid #e5e7eb', flexShrink: 0,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16 }}>Proctor & Ramble</span>
        <Timer startedAt={snapshot.started_at} />
        <button
          onClick={handleEnd}
          style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #e5e7eb',
            background: '#fff', cursor: 'pointer', fontSize: 14,
          }}
        >
          End Interview
        </button>
      </div>

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: '0 0 60%', borderRight: '1px solid #e5e7eb', overflow: 'hidden' }}>
          <QuestionPanel plan={snapshot.plan} />
        </div>
        <div style={{ flex: '0 0 40%', overflow: 'hidden' }}>
          <ProctorPanel interjections={snapshot.interjections} />
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        padding: '8px 24px', borderTop: '1px solid #e5e7eb', fontSize: 12,
        color: '#6b7280', display: 'flex', gap: 16, flexShrink: 0,
      }}>
        <span style={{ color: connected ? '#16a34a' : '#dc2626' }}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
        {snapshot.watch_path && <span>watching: {snapshot.watch_path}</span>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/screens/Interview.tsx
git commit -m "feat: Interview screen with question panel, proctor panel, and timer"
```

---

### Task 16: Feedback screen + export

**Files:**
- Create: `frontend/src/components/ExportButton.tsx`
- Create: `frontend/src/screens/Feedback.tsx`

- [ ] **Step 1: Implement ExportButton**

```tsx
// frontend/src/components/ExportButton.tsx
import type { SessionSnapshot } from '../types/session'

interface Props {
  snapshot: SessionSnapshot
}

function buildInterleaved(snapshot: SessionSnapshot): string {
  type Entry = { timestamp: string; type: string; content: string }
  const entries: Entry[] = []

  for (const chunk of snapshot.transcript) {
    entries.push({ timestamp: chunk.timestamp, type: 'speech', content: chunk.text })
  }
  for (const delta of snapshot.deltas) {
    entries.push({ timestamp: delta.timestamp, type: 'code_change', content: `Path: ${delta.path}\n${delta.diff}` })
  }
  for (const i of snapshot.interjections) {
    entries.push({ timestamp: i.timestamp, type: `interjection_${i.trigger}`, content: i.text })
  }

  entries.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  return JSON.stringify({ session: entries, plan: snapshot.plan }, null, 2)
}

export default function ExportButton({ snapshot }: Props) {
  const handleExport = () => {
    const content = buildInterleaved(snapshot)
    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `interview-${new Date().toISOString().slice(0, 19)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <button
      onClick={handleExport}
      style={{
        padding: '8px 20px', borderRadius: 6, border: '1px solid #e5e7eb',
        background: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600,
      }}
    >
      Export transcript
    </button>
  )
}
```

- [ ] **Step 2: Implement Feedback screen**

```tsx
// frontend/src/screens/Feedback.tsx
import { useEffect, useState } from 'react'
import ExportButton from '../components/ExportButton'
import { useSession } from '../hooks/useSession'
import type { SessionSnapshot } from '../types/session'

interface Props {
  onReset: () => void
}

export default function Feedback({ onReset }: Props) {
  const { fetchSnapshot } = useSession()
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [loadingFeedback, setLoadingFeedback] = useState(false)

  useEffect(() => {
    fetchSnapshot().then(setSnapshot)
  }, [fetchSnapshot])

  const handleGenerateFeedback = async () => {
    if (!snapshot) return
    setLoadingFeedback(true)
    try {
      const res = await fetch('/session/feedback', { method: 'POST' })
      const data = await res.json()
      setFeedback(data.feedback)
    } catch {
      setFeedback('Failed to generate feedback.')
    } finally {
      setLoadingFeedback(false)
    }
  }

  if (!snapshot) return <div style={{ padding: 24 }}>Loading...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid #e5e7eb',
      }}>
        <span style={{ fontWeight: 700, fontSize: 16 }}>Interview Complete</span>
        <div style={{ display: 'flex', gap: 12 }}>
          <ExportButton snapshot={snapshot} />
          <button
            onClick={handleGenerateFeedback}
            disabled={loadingFeedback}
            style={{ padding: '8px 20px', borderRadius: 6, border: 'none', background: '#0070f3', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
          >
            {loadingFeedback ? 'Generating...' : 'Get Feedback'}
          </button>
          <button
            onClick={onReset}
            style={{ padding: '8px 20px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}
          >
            New Interview
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Transcript */}
        <div style={{ flex: '0 0 40%', borderRight: '1px solid #e5e7eb', padding: 24, overflowY: 'auto' }}>
          <h3 style={{ marginTop: 0 }}>Transcript</h3>
          {snapshot.transcript.length === 0 ? (
            <p style={{ color: '#9ca3af' }}>No speech recorded.</p>
          ) : (
            snapshot.transcript.map((chunk, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(chunk.timestamp).toLocaleTimeString()}</span>
                <p style={{ margin: '4px 0', lineHeight: 1.6 }}>{chunk.text}</p>
              </div>
            ))
          )}
        </div>

        {/* Right column: code diffs + feedback */}
        <div style={{ flex: '0 0 60%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, padding: 24, overflowY: 'auto', borderBottom: '1px solid #e5e7eb' }}>
            <h3 style={{ marginTop: 0 }}>Code changes</h3>
            {snapshot.deltas.length === 0 ? (
              <p style={{ color: '#9ca3af' }}>No code changes recorded.</p>
            ) : (
              snapshot.deltas.map((delta, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(delta.timestamp).toLocaleTimeString()} — {delta.path}</span>
                  <pre style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: 12, fontSize: 12, overflowX: 'auto', marginTop: 4 }}>
                    {delta.diff}
                  </pre>
                </div>
              ))
            )}
          </div>

          {feedback && (
            <div style={{ padding: 24, overflowY: 'auto', maxHeight: '40%' }}>
              <h3 style={{ marginTop: 0 }}>Feedback</h3>
              <pre style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: 14 }}>{feedback}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add /session/feedback endpoint to backend/main.py**

Add this route to `backend/main.py` after the `get_snapshot` endpoint:

```python
@app.post("/session/feedback")
async def generate_feedback():
    snap = manager.snapshot
    if not snap.plan:
        raise HTTPException(status_code=400, detail="No interview plan loaded")

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
    return {"feedback": feedback_text}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Run full backend tests**

```bash
cd .. && pytest -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/Feedback.tsx frontend/src/components/ExportButton.tsx backend/main.py
git commit -m "feat: Feedback screen with export, diff timeline, and LLM feedback"
```

---

## End-to-End Verification

1. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`
2. Start backend: `source .venv/bin/activate && uvicorn backend.main:app --reload`
3. Start frontend: `cd frontend && npm run dev`
4. Open `http://localhost:5173`
5. Paste a LeetCode URL and click Load — verify the question loads
6. Enter a watch path to a `.py` file and click Start
7. Speak a few sentences — verify transcript is being captured
8. Save the file — verify a diff appears
9. Wait for a proctor interjection to appear in the right panel
10. Click End Interview — verify the Feedback screen appears
11. Click Get Feedback — verify LLM feedback renders
12. Click Export transcript — verify a `.json` file downloads with interleaved events
