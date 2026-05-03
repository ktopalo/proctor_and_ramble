# Proctor & Ramble

An AI interviewer that recreates the feeling of having a live proctor. It listens to you think out loud, watches your code as you type, and intervenes with Socratic nudges when you're stuck — without just giving you the answer.

At the end you get structured feedback scored against the question's evaluation rubric.

---

## How It Works

1. **Paste a LeetCode (or any coding problem) URL** — the backend fetches it, strips it to plain text, and asks the LLM to extract a structured `InterviewPlan`: problem statement, constraints, hint hierarchy, expected approaches, follow-up questions, and an evaluation rubric.
2. **Point it at your solution file** — the file watcher tracks every save and diffs it against the previous snapshot.
3. **Hit Start** — the microphone opens. Every time you pause speaking or save your file, the agent loop checks in: *should the interviewer say something right now?* If yes, a Socratic nudge appears in the Proctor panel.
4. **End the session** — the full transcript + code diff timeline is sent to the LLM for evaluation. You get scores, strengths, and gaps, plus an exportable JSON/Markdown summary.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, WebSocket |
| Frontend | TypeScript, React (Vite) |
| STT (default) | Groq Whisper API (`whisper-large-v3-turbo`) |
| STT (fallback) | mlx-whisper (Apple Silicon, runs on-device) |
| LLM (default) | OpenAI API (`gpt-4o`) |
| File watching | watchdog |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A microphone
- API keys: `OPENAI_API_KEY` and/or `GROQ_API_KEY` depending on your config

---

## Setup

**1. Clone and install backend dependencies**

```bash
git clone https://github.com/your-username/proctor_and_ramble.git
cd proctor_and_ramble
pip install -e .
```

Or with `uv`:

```bash
uv sync
```

**2. Install frontend dependencies**

```bash
cd frontend
npm install
```

**3. Configure secrets**

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

**4. Configure engines** (optional)

Edit `config.yaml` to switch STT or LLM providers:

```yaml
stt:
  engine: groq_whisper          # or: mlx_whisper (Apple Silicon, no API key needed)
  speech_pause_threshold_seconds: 1

llm:
  provider: openai
  model: gpt-5.5

agent:
  min_seconds_between_interjections: 15
```

---

## Running

Start the backend and frontend in two terminals:

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

---

## Screens

**Setup** — paste a problem URL, select your solution file or directory to watch, pick your models, hit Start.

**Live Interview**

```
┌─────────────────────────────────────────────────────┐
│  Proctor & Ramble                    ⏱  00:23:41    │
├──────────────────────────┬──────────────────────────┤
│                          │                          │
│   QUESTION               │   PROCTOR                │
│                          │                          │
│   Problem statement,     │   Agent nudges,          │
│   constraints, hint      │   newest at top          │
│   hierarchy              │                          │
│                          │                          │
├──────────────────────────┴──────────────────────────┤
│  ● Recording   watching: ~/projects/foo/solution.py │
└─────────────────────────────────────────────────────┘
```

**Feedback** — transcript (left), code diff timeline (right), LLM evaluation with rubric scores below, export button.

---

## Adding a New STT or LLM Backend

All swappable engines follow the base-class pattern:

- **STT**: subclass `BaseSTTEngine` in `backend/engines/`, implement `start()`, `stop()`, and `on_transcript(chunk)`. Register the name in `_build_stt()` in `backend/main.py`.
- **LLM**: subclass `BaseLLMClient`, implement `complete()` and `stream_complete()`. Register in config.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

---

## Project Structure

```
proctor_and_ramble/
├── backend/
│   ├── engines/         # STT + LLM base classes and implementations
│   ├── watcher/         # File watcher (watchdog-based)
│   ├── agent/           # Trigger listener + LLM judge + interjection emitter
│   ├── session/         # SessionManager (single source of truth) + Pydantic models
│   ├── question/        # URL fetch → LLM extract → InterviewPlan
│   └── main.py          # FastAPI app, WebSocket hub, REST endpoints
├── frontend/
│   └── src/
│       ├── screens/     # Setup, Interview, Feedback
│       ├── components/  # Timer, QuestionPanel, ProctorPanel, ExportButton
│       └── hooks/       # useSession (WebSocket + state)
├── config.yaml          # Engine selection and tuning
└── .env.example         # Secret key placeholders
```
