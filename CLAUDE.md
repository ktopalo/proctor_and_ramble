# Claude Code Instructions — Proctor & Ramble

## Architecture Doc

`ARCHITECTURE.md` is the source of truth for this project's design. Update it when making any of the following kinds of changes:

- Adding or removing a backend module (engines, watcher, agent, session, question)
- Changing how components communicate (new WebSocket message types, new REST endpoints)
- Changing the swappable engine interface (`BaseSTTEngine`, `BaseLLMClient`)
- Adding a new screen or significantly restructuring the frontend
- Changing the session data model (`TranscriptChunk`, `FileDelta`, `Interjection`, `InterviewPlan`)
- Changing the config schema

Minor changes (bug fixes, prompt tweaks, styling, adding a config field) do not require an architecture update.

## Project Conventions

- All swappable components follow the base-class pattern: abstract base in `engines/`, concrete impls registered by name in `config.yaml`
- `SessionManager` is the only stateful object — all other components communicate through it
- Backend is Python (FastAPI), frontend is TypeScript/React
- Secrets always come from `.env`, never hardcoded
- Default STT: `mlx-whisper` (Apple Silicon). Default LLM: OpenAI API.
