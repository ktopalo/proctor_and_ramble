# Question Download & Enrichment Redesign

**Date:** 2026-05-03
**Status:** Approved

## Context

The current `InterviewPlan` is a flat structure (`problem_statement`, `constraints`, `hints`, `expected_approaches`, `follow_up_questions`, `rubric: dict`) that gives the agent minimal context and the UI only partial information. The extraction prompt produces shallow, generic output that doesn't serve the agent well.

This redesign splits the plan into a **display zone** (what the candidate sees) and an **agent context zone** (rich hidden context for the proctor), and replaces all structured sub-fields with richer, LLM-friendly content.

## Data Model

### `InterviewPlan` (replaces existing)

```python
class InterviewPlan(BaseModel):
    problem_markdown: str     # full display content — description, inline code fences, immediate constraints
    follow_ups: list[str]     # ordered markdown strings, revealed one at a time during the session
    agent_briefing: str       # rich hidden prose: approaches, gotchas, complexity, when to reveal follow-ups
    rubric: str               # free-form evaluation guide, used on feedback screen only
    source_url: str | None = None
```

All old fields (`constraints`, `hints`, `expected_approaches`, `follow_up_questions`, `rubric: dict`) are removed.

### `SessionSnapshot` addition

```python
revealed_follow_up_count: int = 0  # how many follow_ups have been shown to the candidate so far
```

## Question Loader

### System prompt

```
You are an expert software engineering interviewer preparing a structured brief for a live 
technical coding interview. The candidate is a software engineer. 
Return only valid JSON, no markdown fences.
```

### Extraction prompt

Opens with explicit framing as a technical coding interview for a software engineering candidate, then requests exactly four fields:

```json
{
  "problem_markdown": "full problem in markdown — description, inline code fences, immediate constraints baked in naturally",
  "follow_ups": ["ordered markdown strings: deferred constraints + follow-on questions, gentlest to hardest"],
  "agent_briefing": "rich prose: all known solutions (brute to optimal), time/space complexity, common mistakes, subtle gotchas, what good vs bad looks like at each stage, when/why to surface each follow-up",
  "rubric": "what a strong submission looks like across correctness, efficiency, communication, edge cases"
}
```

`agent_briefing` is the core investment — the LLM writes it as a thorough briefing a senior engineer would prepare before running the interview. No bullet-point restriction, no length limit.

**Implementation note:** Page content truncation raised from 8000 to 12000 chars. LLM call uses `temperature=0` for determinism.

## Agent Loop

### System prompt composition

`agent_briefing` and `rubric` are pulled from `session.snapshot.plan` at call time and prepended to the agent's system prompt. No constructor change to `AgentLoop` is needed — the plan is already accessible via `self._session`. They do not repeat in the per-turn context message.

### Per-turn context

- Elapsed time
- Recent transcript chunks
- Recent file diffs
- Currently revealed follow-ups (so the agent knows what the candidate has already been shown)

### Reveal signal

The agent can return one of three response formats:

| Response | Meaning |
|---|---|
| `NO` | Do not intervene |
| `<interjection text>` | Intervene with this text, no follow-up reveal |
| `REVEAL_NEXT_FOLLOWUP: <optional interjection text>` | Reveal the next follow-up in the UI and optionally deliver an interjection |

When `REVEAL_NEXT_FOLLOWUP` is received, the loop:
1. Increments `revealed_follow_up_count` on the session
2. Emits a `follow_up_revealed` WebSocket event
3. If interjection text is present, also emits an `interjection` event

Follow-ups are revealed when the candidate asks questions that warrant revealing a deferred constraint or follow-on challenge — the agent decides this based on the briefing's guidance. The per-turn context always includes `revealed_follow_up_count` and `total_follow_ups` so the agent knows when all follow-ups are exhausted and stops emitting `REVEAL_NEXT_FOLLOWUP`.

## Frontend

### `QuestionPanel`

- Renders `problem_markdown` using `react-markdown`
- Below the main problem, shows the first `revealed_follow_up_count` items from `plan.follow_ups`, each in a visually distinct inset block with a subtle separator to convey they were added mid-session

### `useSession` hook

Handles the new `follow_up_revealed` WebSocket event by incrementing `revealed_follow_up_count` on the local session snapshot.

### Types

`InterviewPlan` in `frontend/src/types/session.ts` mirrors the new backend model exactly. `WSEventType` gains `'follow_up_revealed'`.

### Feedback screen

`rubric` is a plain string — rendered as markdown on the feedback screen, simpler than the current dict iteration.

## Change Surface

| File | Change |
|---|---|
| `backend/session/models.py` | New `InterviewPlan` fields, `revealed_follow_up_count` on `SessionSnapshot` |
| `backend/question/loader.py` | New system prompt, new extraction prompt, raise page truncation to 12000 |
| `backend/agent/loop.py` | Inject briefing into system prompt, handle `REVEAL_NEXT_FOLLOWUP` signal |
| `backend/agent/prompts.py` | Updated agent instructions explaining the reveal mechanic |
| `frontend/src/types/session.ts` | Mirror new model, add `follow_up_revealed` event type |
| `frontend/src/hooks/useSession.ts` | Handle `follow_up_revealed` event |
| `frontend/src/components/QuestionPanel.tsx` | Markdown rendering, progressive follow-up blocks |
| `frontend/package.json` | Add `react-markdown` if not already present |
