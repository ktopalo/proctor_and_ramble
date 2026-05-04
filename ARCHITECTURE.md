# Proctor & Ramble — Architecture

## What This Is

An AI interviewer that recreates the feeling of having a live proctor. It watches your speech and your code in real time, intervenes intelligently with Socratic nudges, and produces structured feedback at the end. Everything is swappable: STT engine, LLM provider, models.

---

## V1 Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, WebSocket |
| Frontend | TypeScript, React (Vite) |
| STT (default) | Groq Whisper API (`whisper-large-v3-turbo`) |
| STT (fallback) | mlx-whisper (Apple Silicon, on-device) |
| LLM (default) | OpenAI API (`gpt-4o`) |
| LLM (alt) | Codex CLI subprocess wrapper |
| TTS (default) | ElevenLabs API |
| TTS (alt) | Piper (local, offline, free) |
| File watching | watchdog |

**V2 note:** Target native macOS app packaging (Tauri or Swift wrapper) once core is stable. V1 runs as two local processes (backend + frontend dev server).

---

## Communication

- **WebSocket** (`/ws`) — all real-time events: transcript chunks, file deltas, agent interjections, follow-up reveals. Data flows server → client only; the client just sends text keepalives that are discarded.
- **REST** — control actions: load question, start session, end session, get snapshot, generate feedback.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Python Backend                       │
│                                                          │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │  BaseSTTEngine│  │ FileWatcher│  │   AgentLoop     │  │
│  │  (Silero VAD  │  │ (watchdog) │  │  (trigger +     │  │
│  │   + subclass) │  │            │  │   LLM judge)    │  │
│  └──────┬────────┘  └─────┬──────┘  └──────┬──────────┘  │
│         └─────────────────┴────────────────┘            │
│                           │                             │
│                ┌──────────────────┐                     │
│                │  SessionManager  │                     │
│                │  (single source  │                     │
│                │   of truth)      │                     │
│                └──────────┬───────┘                     │
│                           │                             │
│                ┌──────────────────┐                     │
│                │  ConnectionManager│                    │
│                │  (WebSocket hub) │                     │
│                └──────────┬───────┘                     │
└───────────────────────────┼─────────────────────────────┘
                            │ WebSocket
┌───────────────────────────┼─────────────────────────────┐
│           React Frontend  │                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  useSession (WebSocket + REST client + state)      │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌───────────────────────────────────────┐  │
│  │  Setup   │  │  Interview                            │  │
│  │  screen  │  │  QuestionPanel + ProctorPanel + Timer │  │
│  └──────────┘  └───────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Feedback  (transcript + diffs + LLM eval)         │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
proctor_and_ramble/
├── backend/
│   ├── config.py                # Pydantic config loader — reads config.yaml
│   ├── prompts.py               # All LLM prompts live here (PROCTOR, QUESTION_EXTRACTION, QUESTION_SYSTEM)
│   ├── main.py                  # FastAPI app, WebSocket hub, REST endpoints, engine wiring
│   ├── engines/
│   │   ├── stt/
│   │   │   ├── stt_base.py      # Abstract BaseSTTEngine — VAD + audio capture; subclass only transcribe()
│   │   │   ├── groq_whisper.py  # Groq Whisper API (default)
│   │   │   └── mlx_whisper.py   # mlx-whisper on-device (Apple Silicon fallback)
│   │   ├── llm/
│   │   │   ├── llm_base.py      # Abstract BaseLLMClient — complete() + stream_complete()
│   │   │   ├── openai_client.py # OpenAI SDK (default)
│   │   │   └── codex_cli_client.py  # Codex CLI subprocess wrapper
│   │   └── tts/
│   │       ├── tts_base.py      # Abstract BaseTTSEngine — synthesize(text) -> (PCM bytes, sample_rate)
│   │       ├── elevenlabs_tts.py  # ElevenLabs API (default)
│   │       ├── piper_tts.py     # Piper local TTS (offline, free)
│   │       └── player.py        # TTSPlayer — asyncio queue + sounddevice playback
│   ├── watcher/
│   │   └── file_watcher.py      # watchdog-based; diffs on save; bridges sync→async
│   ├── agent/
│   │   └── loop.py              # Cooldown + context builder + LLM judge + interjection emitter
│   ├── session/
│   │   ├── manager.py           # SessionManager — single stateful object, sorted timeline
│   │   └── models.py            # Pydantic: TranscriptChunk, FileDelta, Interjection, InterviewPlan, SessionSnapshot
│   └── question/
│       └── loader.py            # URL fetch → HTML strip → LLM extract → InterviewPlan
├── frontend/
│   └── src/
│       ├── App.tsx              # Screen router: 'setup' | 'interview' | 'feedback'
│       ├── types/
│       │   └── session.ts       # TypeScript interfaces mirroring all Pydantic models + WS event types
│       ├── hooks/
│       │   └── useSession.ts    # WebSocket connection + snapshot state + REST action callbacks
│       ├── screens/
│       │   ├── Setup.tsx        # URL input, question preview (spoilers), watch path, duration, Start
│       │   ├── Interview.tsx    # QuestionPanel + ProctorPanel + Timer + unified transcript toggle
│       │   └── Feedback.tsx     # Transcript + code diffs + LLM feedback + export
│       └── components/
│           ├── QuestionPanel.tsx  # problem_markdown + revealed follow_ups (slice by revealedCount)
│           ├── ProctorPanel.tsx   # Interjection cards, newest-first, with relative timestamps
│           ├── Timer.tsx          # Countdown from timerDuration, starts from started_at
│           ├── ExportButton.tsx   # Downloads interleaved JSON of full session
│           ├── MarkdownText.tsx   # Inline markdown renderer
│           └── Spinner.tsx        # Loading indicator
├── config.yaml                  # Engine selection and tuning (see Config section)
├── .env.example                 # API key placeholders
├── pyproject.toml               # Python package config (uv/pip)
└── uv.lock                      # Locked dependencies
```

---

## Core Components

### Config (`backend/config.py`)

Loaded once at startup via `load_config("config.yaml")`. Parsed into Pydantic models:

```python
class STTConfig:
    engine: str                          # "groq_whisper" | "mlx_whisper"
    model: str
    speech_pause_threshold_seconds: float  # default 3.0

class LLMConfig:
    provider: str                        # "openai" | "codex_cli"
    model: str
    codex_path: str                      # default "codex" — path to codex binary

class AgentConfig:
    min_seconds_between_interjections: int  # default 30

class ServerConfig:
    host: str; port: int                 # default 127.0.0.1:8000

class FrontendConfig:
    port: int                            # default 5173

class TTSConfig:
    enabled: bool                        # default True — set False to disable TTS entirely
    provider: str                        # "elevenlabs" | "piper"
    voice_id: str                        # ElevenLabs voice ID (e.g. "Rachel")
    model_id: str                        # ElevenLabs model (e.g. "eleven_monolingual_v1")
    model_path: str                      # Piper .onnx model file path (piper only)
```

---

### Session Data Models (`backend/session/models.py`)

All session data is expressed in these Pydantic models. The frontend mirrors these in `frontend/src/types/session.ts`.

```python
TranscriptChunk:
    text: str
    timestamp: datetime          # UTC, auto-set on creation
    duration_seconds: float      # duration of the audio segment

FileDelta:
    path: str                    # absolute resolved path
    diff: str                    # ndiff format (lines prefixed with "  ", "+ ", "- ", "? ")
    timestamp: datetime

Interjection:
    text: str
    timestamp: datetime
    trigger: str                 # "speech_pause" | "file_save"

InterviewPlan:
    problem_markdown: str        # what the candidate sees — no hints
    follow_ups: list[str]        # ordered list of escalating challenges, revealed one at a time
    agent_briefing: str          # full interviewer brief: approaches, edge cases, timing guidance
    rubric: str                  # evaluation guide for feedback generation
    source_url: str | None       # original URL the plan was loaded from

SessionSnapshot:
    transcript: list[TranscriptChunk]
    deltas: list[FileDelta]
    interjections: list[Interjection]
    plan: InterviewPlan | None
    started_at: datetime | None
    ended_at: datetime | None
    watch_path: str | None
    revealed_follow_up_timestamps: list[datetime]   # length = number of follow-ups revealed so far
```

---

### Session Manager (`backend/session/manager.py`)

The **only stateful object** in the system. All other components are stateless and communicate through it.

The manager holds `snapshot: SessionSnapshot` plus an internal `_timeline_events: list[tuple[datetime, str]]`, sorted chronologically using `bisect.insort`.

**Key methods:**

| Method | What it does |
|---|---|
| `start(watch_path)` | Resets snapshot, preserves the loaded plan |
| `end()` | Sets `ended_at` |
| `set_plan(plan)` | Sets `snapshot.plan` (called before `start`) |
| `add_transcript_chunk(chunk)` | Appends to `snapshot.transcript`, inserts `[MM:SS] SPEECH: ...` into timeline |
| `add_file_delta(delta)` | Appends to `snapshot.deltas`, inserts `[MM:SS] CODE filename (+N -N):` with indented diff |
| `add_interjection(interjection)` | Appends to `snapshot.interjections`, inserts `[MM:SS] PROCTOR: ...` into timeline |
| `reveal_next_follow_up(follow_up_text)` | Appends to `revealed_follow_up_timestamps`, inserts `[MM:SS] FOLLOW_UP_REVEALED: ...` |
| `timeline_text` (property) | Returns sorted timeline as a single string headed `TIMELINE:` |

The timeline is the primary context passed to the LLM agent. All timestamps are rendered as session offsets (`[MM:SS]`), not wall-clock times.

**Important:** `start()` preserves the current plan so that the question can be loaded before the session starts without being wiped.

---

### STT Engine (`backend/engines/stt/`)

#### Base class (`stt_base.py`)

`BaseSTTEngine` handles all audio capture and VAD logic. Subclasses only implement `transcribe(audio: np.ndarray) -> str`.

**Audio pipeline constants:**
- Sample rate: `16000 Hz`
- Block size: `512 samples` (32ms) — required by Silero VAD
- Max buffer: `30 seconds` — hard cap, flushes early if reached

**VAD setup (Silero VAD):**
- threshold: `0.5`
- min_silence_duration_ms: derived from `pause_threshold_seconds` config × 1000
- speech_pad_ms: `30`

**Audio callback (called by sounddevice on the audio thread):**
1. Feed 512-sample chunk as a `torch.Tensor` to `VADIterator`
2. If `"start"` event: set `_speaking = True`
3. If `"end"` event and buffer non-empty: call `_flush(pause=True)`
4. While speaking: accumulate samples into `_speech_buffer`
5. If buffer exceeds 30s: call `_flush(pause=False)` (hard cap, no speech pause triggered)

**`_flush(pause)`:**
- Snapshots and clears `_speech_buffer`, sets `_speaking = False`
- Dispatches `_transcribe_and_notify(audio, pause)` to the asyncio event loop via `asyncio.run_coroutine_threadsafe`

**`_transcribe_and_notify(audio, pause)`:**
1. Calls `self.transcribe(audio)` (abstract — implemented by subclass)
2. If `text` is non-empty: fires `_on_transcript(TranscriptChunk(...))`
3. If `pause=True`: fires `_on_speech_pause()` regardless of whether text was empty

The `_on_transcript` and `_on_speech_pause` callbacks are injected by `main.py` via `set_on_transcript()` and `set_on_speech_pause()`.

**To add a new STT backend:**
1. Subclass `BaseSTTEngine` in `backend/engines/stt/`
2. Implement `transcribe(self, audio: np.ndarray) -> str` — audio is float32 16kHz mono
3. Register a new engine name in `_build_stt()` in `backend/main.py`
4. Add the engine name to `config.yaml`

#### `GroqWhisperEngine` (`groq_whisper.py`)

- Default engine. Reads `GROQ_API_KEY` from env.
- `transcribe()`: encodes float32 audio → WAV (PCM int16, mono, 16kHz) in-memory → posts to `groq.audio.transcriptions.create` with `response_format="text"` and `language="en"`.

#### `MLXWhisperEngine` (`mlx_whisper.py`)

- Apple Silicon on-device fallback. No API key needed.
- `transcribe()`: calls `mlx_whisper.transcribe(audio, path_or_hf_repo=model)` directly.

---

### TTS Engine (`backend/engines/tts/`)

Converts proctor interjection text to audio, played through the machine's default output device. Follows the same abstract-base + factory pattern as STT and LLM.

#### Base class (`tts_base.py`)

```python
class BaseTTSEngine(ABC):
    async def synthesize(self, text: str) -> tuple[bytes, int]:
        # Returns (raw 16-bit PCM bytes, sample_rate_hz)
        ...
    async def close(self) -> None: ...
```

#### `TTSPlayer` (`player.py`)

Wraps a `BaseTTSEngine`. Owns an `asyncio.Queue[str]`; the worker loop dequeues text, calls `engine.synthesize()`, and plays PCM via `sounddevice.play()` + `sd.wait()` (in a thread executor). Errors are logged and skipped — TTS failure never blocks the session.

Started on FastAPI `startup`, stopped on `shutdown`. Wired into `_on_interjection()` in `main.py`: after broadcasting the `interjection` WebSocket event, `tts_player.enqueue(interjection.text)` is called.

#### `ElevenLabsTTSEngine` (`elevenlabs_tts.py`)

- Calls `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_22050`
- Returns raw 16-bit PCM at 22050 Hz directly — no decoding step needed
- API key from `ELEVENLABS_API_KEY` env var
- Config: `tts.voice_id`, `tts.model_id`

#### `PiperTTSEngine` (`piper_tts.py`)

- Wraps `piper-tts` Python package (optional dep: `pip install 'proctor_and_ramble[piper]'`)
- Synthesis is CPU-bound; runs via `run_in_executor`
- Requires a `.onnx` voice model file in `models/piper/` (gitignored, downloaded separately)
- Config: `tts.model_path`

**To add a new TTS backend:**
1. Subclass `BaseTTSEngine` in `backend/engines/tts/`
2. Implement `async synthesize(text) -> (pcm_bytes, sample_rate)`
3. Add a branch to `_build_tts()` in `backend/main.py`
4. Add any new config fields to `TTSConfig` in `backend/config.py`

---

### LLM Client (`backend/engines/llm/`)

#### Base class (`llm_base.py`)

```python
class BaseLLMClient(ABC):
    async def complete(messages, system_prompt="") -> str
    async def stream_complete(messages, system_prompt="") -> AsyncIterator[str]
```

`messages` is a standard OpenAI-style list: `[{"role": "user"|"assistant", "content": "..."}]`. The system prompt is always injected as `{"role": "system", ...}` prepended to the message list.

**To add a new LLM backend:**
1. Subclass `BaseLLMClient` in `backend/engines/llm/`
2. Implement `complete()` and `stream_complete()`
3. Register a new `provider` name in `_build_llm()` in `backend/main.py`
4. Add `codex_path`-style config fields to `LLMConfig` if the provider needs extra config

#### `OpenAIClient` (`openai_client.py`)

- Wraps `AsyncOpenAI`. Reads `OPENAI_API_KEY` from env (passed in at construction).
- `complete()`: non-streaming `chat.completions.create`.
- `stream_complete()`: streaming `chat.completions.create`, yields token by token.

#### `CodexCLIClient` (`codex_cli_client.py`)

- Wraps the `codex` CLI binary as a subprocess. No OpenAI API key needed (uses the user's ChatGPT subscription via Codex CLI).
- Prepends `/opt/homebrew/bin` to `PATH` so the binary is found when running as a subprocess.
- `complete()`:
  1. Builds a plain-text prompt from system + messages (format: `System: ...\n\nUser: ...`)
  2. Writes prompt to stdin of `codex exec --ephemeral --ignore-user-config --ignore-rules -m <model> -s read-only -o <tempfile> -`
  3. Reads the output from the temp file and returns it
- `stream_complete()`: not natively supported — yields the full `complete()` result as a single chunk.

---

### File Watcher (`backend/watcher/file_watcher.py`)

Watches a file or directory for changes using `watchdog`. Bridges the watchdog observer thread to the asyncio event loop.

**Initialization:**
- Resolves the path and determines if it's a file or directory.
- Pre-populates `_last_content` dict with current file contents so the first diff is against the initial state.

**On file change:**
1. Reads new content (`_read_file` silently handles `FileNotFoundError`, `PermissionError`, `UnicodeDecodeError` by returning `""`)
2. Runs `difflib.ndiff` against the previous snapshot
3. Filters out `? ` hint lines from ndiff output
4. If there are any `+ ` or `- ` lines: creates `FileDelta`, updates `_last_content`, dispatches via `asyncio.run_coroutine_threadsafe`
5. If no meaningful changes: silently drops (handles spurious save events)

**Diff format:** `ndiff` (not unified diff). Lines are prefixed:
- `  ` — unchanged
- `+ ` — added
- `- ` — removed
- `? ` — ndiff hints (filtered out before storing)

**Directory mode:** `_Handler` fires on `on_modified` and `on_created` (both non-directory). In directory mode, all files under the path are tracked recursively.

---

### Agent Loop (`backend/agent/loop.py`)

Evaluates whether the proctor should intervene after each trigger. Triggers arrive from two sources:
- `on_speech_pause()` — called by the STT engine after each pause-ended segment
- `on_file_save()` — called by `_handle_file_delta` in `main.py` after each file change

**Cooldown:** Skips evaluation entirely if an interjection was emitted less than `min_seconds_between_interjections` seconds ago. The cooldown timer resets on any interjection OR on a follow-up reveal.

**Context building (`_build_context`):**
1. `TIME ELAPSED: Xm Ys` — session duration
2. `FOLLOW-UPS REVEALED: N of M` — so the LLM knows how many follow-ups remain
3. Full `timeline_text` from `SessionManager` — chronological interleaved log of speech, code changes, proctor messages, and follow-up reveals

**System prompt construction:**
- Base: `PROCTOR_SYSTEM_PROMPT` from `backend/prompts.py`
- If a plan is loaded: appended with `INTERVIEW BRIEF:\n{plan.agent_briefing}\n\nRUBRIC:\n{plan.rubric}`

**LLM response protocol (exact string matching):**

| Response | Action |
|---|---|
| `"NO"` (case-insensitive) | Silent — no interjection |
| Starts with `"REVEAL_NEXT_FOLLOWUP"` | Reveal next follow-up; if text after `:` is non-empty, also emit interjection |
| Any other text | Emit as interjection directly |

For `REVEAL_NEXT_FOLLOWUP`:
- Calls `session.reveal_next_follow_up(follow_up_text)` — appends to `revealed_follow_up_timestamps` and timeline
- Fires `on_follow_up_revealed()` callback → WebSocket `follow_up_revealed` event → frontend reveals next follow-up in QuestionPanel
- Resets cooldown timer

---

### Prompts (`backend/prompts.py`)

All LLM prompts are centralized here. There are three:

**`PROCTOR_SYSTEM_PROMPT`** — used by `AgentLoop`. Instructs the LLM to behave as a silent, Socratic interviewer. Key behaviors defined by the prompt:
- Default: return exactly `"NO"`
- When candidate bounces an idea: one probing question using "What happens if...", "How would you handle..."
- When candidate asks for help: brief, human, guiding question
- When candidate claims completion: check the code for edge cases, ask targeted question about any issue found (without naming the bug), or reveal next follow-up if code appears correct
- When candidate is stuck: one redirect sentence, never reveal the approach
- Follow-up reveal rules: use `REVEAL_NEXT_FOLLOWUP` or `REVEAL_NEXT_FOLLOWUP: <message>`; prefer revealing over pushing defensive coding unless the rubric identifies that as a key signal

**`QUESTION_EXTRACTION_PROMPT`** and **`QUESTION_SYSTEM_PROMPT`** — used by `question/loader.py`. The extraction prompt instructs the LLM to return JSON with exactly four fields: `problem_markdown`, `follow_ups`, `agent_briefing`, `rubric`. Explicitly prohibits including hints or solution direction in `problem_markdown`.

---

### Question Loader (`backend/question/loader.py`)

1. Fetches the URL with `httpx` (10s timeout, follows redirects)
2. Strips HTML using a minimal `HTMLParser` subclass that skips `<script>` and `<style>` tag content
3. Truncates to `12,000 characters`
4. Sends to LLM with `QUESTION_EXTRACTION_PROMPT + page_text` as the user message
5. Parses the JSON response into `InterviewPlan`

The LLM is expected to return valid JSON with no markdown fences — enforced by `QUESTION_SYSTEM_PROMPT`. If `json.loads` fails, the error is logged and propagated as-is.

---

### WebSocket Hub (`backend/main.py` — `ConnectionManager`)

`ConnectionManager` holds a list of active `WebSocket` connections. `broadcast(message: dict)` sends JSON to all connections; if a send fails, the connection is silently removed.

The WebSocket endpoint (`/ws`) accepts connections, then loops on `receive_text()` (client keepalives) until `WebSocketDisconnect` is raised.

**All server-to-client message types:**

| `type` field | When sent | `data` payload |
|---|---|---|
| `plan_loaded` | `POST /question/load` succeeds | Full `InterviewPlan` as dict |
| `session_started` | `POST /session/start` succeeds | `{}` |
| `session_ended` | `POST /session/end` succeeds | `{}` |
| `transcript_chunk` | STT emits a segment | `TranscriptChunk` as dict |
| `file_delta` | File watcher detects a save | `FileDelta` as dict |
| `interjection` | Agent loop decides to intervene | `Interjection` as dict |
| `follow_up_revealed` | Agent loop reveals a follow-up | `{}` |

---

### REST Endpoints (`backend/main.py`)

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/question/load` | `{"url": str}` | `{"status": "ok", "plan": InterviewPlan}` |
| `POST` | `/session/start` | `{"watch_path": str}` | `{"status": "started"}` |
| `POST` | `/session/end` | — | `{"status": "ended"}` |
| `GET` | `/session/snapshot` | — | Full `SessionSnapshot` as JSON |
| `POST` | `/session/feedback` | — | `{"feedback": str}` |

`/session/feedback` is an inline LLM call in `main.py` (not in a separate module). It concatenates the full transcript as a single string, all diffs with newlines, and all interjection texts, then sends to the LLM for evaluation against the rubric.

**CORS:** Configured to allow `http://localhost:5173` only.

---

### Session Lifecycle

```
PRE-SESSION
  POST /question/load
    → httpx fetches URL, HTMLParser strips to text (≤12000 chars)
    → LLM extracts InterviewPlan JSON
    → SessionManager.set_plan(plan)
    → WS broadcast: plan_loaded

POST /session/start {watch_path}
    → SessionManager.start(watch_path)     (resets snapshot, preserves plan)
    → AgentLoop instantiated
    → FileWatcher instantiated + started
    → STT engine instantiated, callbacks wired:
        set_on_transcript → _handle_transcript_chunk
        set_on_speech_pause → AgentLoop.on_speech_pause
    → STT engine started (opens sounddevice stream, resets VAD)
    → WS broadcast: session_started

LIVE INTERVIEW
  Mic audio (32ms blocks, 16kHz)
    → Silero VAD detects speech start/end
    → On end: _flush() → transcribe() → TranscriptChunk
    → SessionManager.add_transcript_chunk
    → WS broadcast: transcript_chunk
    → AgentLoop.on_speech_pause() triggered

  File save
    → FileWatcher._on_file_changed
    → ndiff against last snapshot
    → FileDelta
    → SessionManager.add_file_delta
    → WS broadcast: file_delta
    → AgentLoop.on_file_save() triggered

  AgentLoop._maybe_intervene (on either trigger)
    → cooldown check (skip if < min gap since last interjection)
    → build context: time elapsed + follow-ups revealed + full timeline_text
    → LLM call with PROCTOR_SYSTEM_PROMPT + agent_briefing + rubric
    → parse response:
        "NO" → silent
        "REVEAL_NEXT_FOLLOWUP[: msg]"
          → SessionManager.reveal_next_follow_up
          → WS broadcast: follow_up_revealed
          → optional Interjection if msg present
        other → Interjection
    → if Interjection: SessionManager.add_interjection + WS broadcast: interjection
                       + tts_player.enqueue(interjection.text) → spoken aloud

POST /session/end
    → STT engine stopped, FileWatcher stopped
    → SessionManager.end()
    → WS broadcast: session_ended

POST /session/feedback  (optional, triggered from Feedback screen)
    → SessionManager.snapshot assembled
    → LLM evaluates transcript + diffs + interjections against rubric
    → Returns feedback text (markdown)
```

---

## Frontend

### Screen Router (`App.tsx`)

Simple `useState` state machine — no React Router. Three screens: `'setup'` → `'interview'` → `'feedback'`. The timer duration (set on Setup) is passed as `timerDuration` props to Interview.

### `useSession` Hook (`hooks/useSession.ts`)

Each screen that mounts instantiates its own `useSession`, which opens a new WebSocket connection to `ws://127.0.0.1:8000/ws`. The hook maintains a local `snapshot: SessionSnapshot` that is updated by incoming WS events.

**WS event handlers update snapshot state:**
- `plan_loaded` → `snapshot.plan = msg.data`
- `session_started` → `snapshot.started_at = now`
- `session_ended` → `snapshot.ended_at = now`
- `transcript_chunk` → append to `snapshot.transcript`
- `file_delta` → append to `snapshot.deltas`
- `interjection` → **prepend** to `snapshot.interjections` (newest-first for ProctorPanel)
- `follow_up_revealed` → append to `snapshot.revealed_follow_up_timestamps`

**REST action callbacks** exposed by the hook:
- `loadQuestion(url)` → `POST /question/load`
- `startSession(watchPath)` → `POST /session/start`
- `endSession()` → `POST /session/end`
- `fetchSnapshot()` → `GET /session/snapshot` — used by Interview and Feedback on mount to re-hydrate state

**Note:** Because each screen instantiates its own `useSession`, Interview calls `fetchSnapshot()` on mount to pick up the plan and watch_path that were set during Setup (since that WS connection is now closed).

### Setup Screen (`screens/Setup.tsx`)

1. URL input → Load button → `loadQuestion()` → shows `QuestionPreview` with spoiler sections for follow-ups, rubric, and agent briefing
2. Watch path input + duration picker
3. Start button (enabled only when plan is loaded and watch path is set) → `startSession()` → `onStart(durationSeconds)`

### Interview Screen (`screens/Interview.tsx`)

Two-panel layout (60/40 split):
- **QuestionPanel** (60%): renders `plan.problem_markdown` + `plan.follow_ups.slice(0, revealedCount)` — follow-ups appear progressively as `revealed_follow_up_timestamps.length` increases
- **ProctorPanel** (40%): renders `interjections` array (already newest-first from hook) as cards with relative timestamps

Status bar shows connection state + `watch_path`. A collapsible transcript drawer shows the last 20 events of the unified timeline (speech, code, proctor), newest-first.

### Feedback Screen (`screens/Feedback.tsx`)

- Fetches snapshot on mount
- Left 40%: transcript chunks, chronological
- Right 60%: code diffs (pre-formatted ndiff), with feedback panel below when generated
- "Get Feedback" → `POST /session/feedback` → displays markdown result
- "Export transcript" → downloads JSON via `ExportButton`

### ExportButton (`components/ExportButton.tsx`)

Merges transcript, deltas, and interjections into a single array sorted by timestamp:

```json
{
  "session": [
    {"timestamp": "...", "type": "speech", "content": "..."},
    {"timestamp": "...", "type": "code_change", "content": "Path: ...\n<diff>"},
    {"timestamp": "...", "type": "interjection_speech_pause", "content": "..."},
    {"timestamp": "...", "type": "interjection_file_save", "content": "..."}
  ],
  "plan": { ... }
}
```

Downloaded as `interview-<ISO-timestamp>.json`.

---

## Configuration (`config.yaml`)

Full schema with all fields and defaults:

```yaml
stt:
  engine: groq_whisper          # "groq_whisper" | "mlx_whisper"
  model: whisper-large-v3       # model name passed to the engine
  speech_pause_threshold_seconds: 1.0  # Silero VAD min_silence_duration

llm:
  provider: openai              # "openai" | "codex_cli"
  model: gpt-4o                 # model name passed to the provider
  codex_path: codex             # path to codex binary (codex_cli only)

agent:
  min_seconds_between_interjections: 15  # cooldown between any two interjections

server:
  host: 127.0.0.1
  port: 8000

frontend:
  port: 5173                    # informational only — not read by backend

tts:
  enabled: true
  provider: elevenlabs          # "elevenlabs" | "piper"
  voice_id: Rachel              # ElevenLabs voice ID
  model_id: eleven_monolingual_v1
  model_path: models/piper/en_US-amy-medium.onnx  # Piper only
```

Secrets in `.env` (never committed):
```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
ELEVENLABS_API_KEY=sk_...
```

---

## Adding New Components

### New STT Engine

```python
# backend/engines/stt/my_engine.py
from backend.engines.stt.stt_base import BaseSTTEngine
import numpy as np

class MySTTEngine(BaseSTTEngine):
    def __init__(self, model: str, pause_threshold_seconds: float = 1.0):
        super().__init__(pause_threshold_seconds=pause_threshold_seconds)
        # init your client here

    def transcribe(self, audio: np.ndarray) -> str:
        # audio: float32, 16kHz, mono
        # return transcribed text (empty string if nothing to transcribe)
        ...
```

Then in `backend/main.py`, add to `_build_stt()`:
```python
if config.stt.engine == "my_engine":
    from backend.engines.stt.my_engine import MySTTEngine
    return MySTTEngine(model=config.stt.model, pause_threshold_seconds=config.stt.speech_pause_threshold_seconds)
```

### New LLM Backend

```python
# backend/engines/llm/my_client.py
from backend.engines.llm.llm_base import BaseLLMClient
from typing import AsyncIterator

class MyLLMClient(BaseLLMClient):
    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        ...

    async def stream_complete(self, messages: list[dict], system_prompt: str = "") -> AsyncIterator[str]:
        ...
```

Then in `backend/main.py`, add to `_build_llm()`:
```python
if config.llm.provider == "my_provider":
    from backend.engines.llm.my_client import MyLLMClient
    return MyLLMClient(model=config.llm.model)
```

Add any new config fields to `LLMConfig` in `backend/config.py`.

---

## Out of Scope (V1)

- Streaming TTS (lower latency for long interjections — V2)
- Interrupting TTS when user speech is detected (V2)
- Frontend audio controls (play/pause/replay, volume — V2)
- Image captioning / Excalidraw for system design interviews (V2)
- Native macOS app packaging — Tauri or Swift wrapper (V2)
- Multi-question sessions / question banks (V2)
- Cloud deployment (local-only V1)
- `stream_complete` usage in the UI — currently all LLM calls use `complete()` (V2)
