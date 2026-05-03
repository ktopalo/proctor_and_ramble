# Proctor & Ramble — Architecture

## What This Is

An AI interviewer that recreates the feeling of having a live proctor. It watches your speech and your code in real time, intervenes intelligently with Socratic nudges, and produces structured feedback at the end. Everything is swappable: STT engine, LLM provider, models.

---

## V1 Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, WebSocket |
| Frontend | TypeScript, React (Vite) |
| STT (default) | Groq Whisper API (`whisper-large-v3-turbo`) — fallback: mlx-whisper on Apple Silicon |
| LLM (default) | OpenAI API (`gpt-4o`) |
| File watching | watchdog |

**V2 note:** Target native macOS app packaging (Tauri or Swift wrapper) once core is stable. V1 runs as two local processes (backend + frontend dev server).

---

## Communication

- **WebSocket** — all real-time events: transcript chunks, file deltas, agent interjections
- **REST** — control actions: start session, load question, end session

---

## System Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Python Backend                      │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ STT Engine  │  │ FileWatcher│  │  AgentLoop    │  │
│  │ (mlx-       │  │ (watchdog) │  │  (triggers +  │  │
│  │  whisper)   │  │            │  │   LLM judge)  │  │
│  └──────┬──────┘  └─────┬──────┘  └──────┬────────┘  │
│         └───────────────┴────────────────┘           │
│                         │                            │
│               ┌──────────────────┐                   │
│               │  SessionManager  │                   │
│               │  (single source  │                   │
│               │   of truth)      │                   │
│               └──────────┬───────┘                   │
│                          │                           │
│               ┌──────────────────┐                   │
│               │  FastAPI +       │                   │
│               │  WebSocket hub   │                   │
│               └──────────┬───────┘                   │
└──────────────────────────┼────────────────────────────┘
                           │ WebSocket
┌──────────────────────────┼────────────────────────────┐
│            React Frontend│                             │
│  ┌───────────────────────────────────────────────┐   │
│  │  Question Panel │ Timer │ Agent Interjections  │   │
│  └───────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
proctor_and_ramble/
├── backend/
│   ├── engines/
│   │   ├── stt_base.py          # Abstract: start(), stop(), on_transcript(chunk)
│   │   ├── mlx_whisper.py       # mlx-whisper impl (Apple Silicon)
│   │   ├── llm_base.py          # Abstract: complete(messages, system) -> str
│   │   └── openai_client.py     # OpenAI SDK impl, reads OPENAI_API_KEY from env
│   ├── watcher/
│   │   └── file_watcher.py      # watchdog-based; emits FileDelta on save
│   ├── agent/
│   │   └── loop.py              # Trigger listener + LLM judge + interjection emitter
│   ├── session/
│   │   ├── manager.py           # Single source of truth for all session state
│   │   └── models.py            # Pydantic: TranscriptChunk, FileDelta, Interjection, InterviewPlan
│   ├── question/
│   │   └── loader.py            # URL fetch → LLM extract + enrich → InterviewPlan
│   └── main.py                  # FastAPI app, WebSocket hub, REST endpoints
├── frontend/
│   └── src/
│       ├── screens/
│       │   ├── Setup.tsx         # URL input, path selector, model config, Start
│       │   ├── Interview.tsx     # Question panel, timer, proctor panel, status bar
│       │   └── Feedback.tsx      # Transcript, diff timeline, LLM feedback, export
│       ├── components/
│       │   ├── Timer.tsx
│       │   ├── QuestionPanel.tsx
│       │   ├── ProctorPanel.tsx  # Interjection cards, newest at top
│       │   └── ExportButton.tsx  # Serializes session to JSON/Markdown
│       └── hooks/
│           └── useSession.ts     # WebSocket connection + session state
├── ARCHITECTURE.md              # This file
├── CLAUDE.md                    # Claude Code instructions for this repo
├── config.yaml                  # Engine selection and tuning
└── .env.example                 # Secret key placeholders
```

---

## Core Components

### STT Engine (swappable)

`BaseSTTEngine` — interface for all STT implementations:
- `start()` — begin audio capture
- `stop()` — end audio capture
- `on_transcript(chunk: TranscriptChunk)` — callback fired on each transcribed segment

`GroqWhisperEngine` — default impl. Captures mic audio locally via sounddevice, batches it on silence (or at a 30-second hard cap), and sends WAV bytes to the Groq Whisper API. Requires `GROQ_API_KEY` in env.

`MLXWhisperEngine` — Apple Silicon local fallback. Runs mlx-whisper on-device. Set `engine: mlx_whisper` in config to use.

To add a new STT backend: subclass `BaseSTTEngine`, register the name in `_build_stt()` in `main.py`, and add it to `config.yaml`.

### LLM Client (swappable)

`BaseLLMClient` — interface for all LLM providers:
- `complete(messages, system_prompt) -> str`
- `stream_complete(messages, system_prompt) -> AsyncIterator[str]`

`OpenAIClient` — default impl. Wraps the OpenAI Python SDK, reads `OPENAI_API_KEY` from env.

To add a new LLM backend: subclass `BaseLLMClient`, register the name in config.

### File Watcher

Monitors a user-specified file or directory using `watchdog`. On each save, diffs new content against the previous snapshot (unified diff format) and emits a `FileDelta` to `SessionManager`.

### Agent Loop

Listens for two trigger types: `SpeechPause` and `FileSave`. On each trigger:
1. **Cooldown check** — skip if an interjection was emitted less than `min_seconds_between_interjections` ago
2. **Build context** — last N transcript chunks, recent file diffs, full `InterviewPlan`, elapsed time
3. **LLM judge** — ask: *"Should the interviewer say something right now? If yes, what? Be Socratic — nudge, don't solve."*
4. If yes: emit `Interjection` → `SessionManager` → WebSocket → UI

### Session Manager

The only stateful object. All other components are stateless and communicate through it.

Holds:
- `transcript: list[TranscriptChunk]`
- `deltas: list[FileDelta]`
- `interjections: list[Interjection]`
- `plan: InterviewPlan`
- `started_at: datetime`, `ended_at: datetime | None`

### Question Loader

1. Fetches URL content and strips to plain text
2. Sends to LLM to extract and enrich into a structured `InterviewPlan`:
   - Problem statement + constraints
   - Hints hierarchy (subtle → direct)
   - Expected solution approaches
   - Follow-up questions the interviewer might ask
   - Evaluation rubric (correctness, efficiency, communication, edge cases)

---

## Session Data Flow

```
SETUP
  User pastes URL → question/loader.py → InterviewPlan
  User sets watch path
  User hits Start → SessionManager init, STT starts, FileWatcher attaches, AgentLoop begins

LIVE INTERVIEW
  Mic audio  → STT engine   → TranscriptChunk → SessionManager
  File save  → FileWatcher  → FileDelta       → SessionManager
                                                      ↓
                                     AgentLoop detects trigger
                                                      ↓
                                  cooldown check passes?
                                                      ↓
                                     LLM: intervene? + content
                                                      ↓
                              Yes → Interjection → WebSocket → UI
                              No  → silent

FEEDBACK
  User ends session → full snapshot → LLM evaluation against rubric
  → structured feedback (strengths, gaps, rubric scores)
  → export: interleaved JSON/Markdown transcript (portable to any LLM)
```

---

## UI Screens

**Setup** — URL input, watch path selector, model config, Start button.

**Live Interview:**
```
┌─────────────────────────────────────────────────────┐
│  Proctor & Ramble                    ⏱  00:23:41    │
├──────────────────────────┬──────────────────────────┤
│                          │                          │
│   QUESTION               │   PROCTOR                │
│   (~60% width)           │   (~40% width)           │
│                          │                          │
│   Problem statement,     │   Agent interjections,   │
│   constraints, hint      │   newest at top,         │
│   hierarchy              │   subtle card style      │
│                          │                          │
├──────────────────────────┴──────────────────────────┤
│  ● Recording   watching: ~/projects/foo/solution.py │
└─────────────────────────────────────────────────────┘
```

**Feedback** — transcript (left), code diff timeline (right), LLM feedback (below), export button.

---

## Configuration

```yaml
# config.yaml
stt:
  engine: mlx_whisper
  model: mlx-community/whisper-large-v3-mlx
  speech_pause_threshold_seconds: 3

llm:
  provider: openai
  model: gpt-4o

agent:
  min_seconds_between_interjections: 30
  context_transcript_chunks: 20
  context_recent_deltas: 5

server:
  host: 127.0.0.1
  port: 8000

frontend:
  port: 5173
```

Secrets in `.env` (never committed):
```
OPENAI_API_KEY=sk-...
```

---

## Out of Scope (V1)

- TTS for agent interjections (V2)
- Image captioning / Excalidraw for system design interviews (V2)
- Native macOS app packaging (V2)
- Multi-question sessions / question banks (V2)
- Cloud deployment (local only)
