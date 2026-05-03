# Agent Loop — Chronological Context Design

**Date:** 2026-05-03
**Status:** Approved

---

## Problem

The current `AgentLoop._build_context` sends the LLM two disconnected lists:

```
RECENT SPEECH: chunk1 chunk2 chunk3...
RECENT CODE CHANGES: diff1\ndiff2\n...
```

This has three concrete failures:

1. **No temporal ordering.** The model cannot tell when speech and code events occurred relative to each other. It cannot observe cause-and-effect ("candidate said they'd use a hash map, then immediately wrote a linked list").
2. **Prior interjections are invisible.** The model has no idea what nudges it already gave, so it may repeat itself verbatim or ignore whether a prior intervention landed.
3. **Trajectory is lost.** The model cannot reason about whether the candidate is progressing, regressing, or spinning — only the last N events are presented with no temporal structure.

---

## Design

### Core Change: Interleaved Chronological Timeline

`_build_context` is rewritten to merge all three event types from `SessionManager` — `TranscriptChunk`, `FileDelta`, and `Interjection` — into a single list sorted by `timestamp`, then rendered as a unified timeline.

**Full context structure sent to the LLM:**

```
[system prompt — unchanged]

PROBLEM: ...
CONSTRAINTS:
- ...
HINTS (for your reference only — do not reveal):
- (level 1) ...
- (level 2) ...
TIME ELAPSED: 12m 34s

TIMELINE:
[00:42] SPEECH: "I think I'll use a hash map here"
[01:15] CODE main.py (+3 -0):
  + seen = {}
  + for num in nums:
  +     seen[num] = i
[02:30] SPEECH: "Wait, I need to return the indices not just check existence"
[04:00] PROCTOR: "Have you considered what happens with duplicate values?"
[04:18] SPEECH: "Oh right, the problem says exactly one solution so duplicates can't appear"
[05:10] CODE main.py (+1 -1):
  - seen[num] = True
  + seen[num] = i
```

### Event Rendering

| Source | Label | Content |
|---|---|---|
| `TranscriptChunk` | `SPEECH:` | `chunk.text` |
| `FileDelta` | `CODE path (+N -N):` | full diff |
| `Interjection` | `PROCTOR:` | `interjection.text` |

Timestamps are rendered as `[MM:SS]` elapsed from `session.started_at`. All three event types already carry a `timestamp` field — no model changes needed.

**Full diffs are always included.** No line-count trimming. This is intentional: the LLM needs the complete picture to reason about code direction, not just that something changed.

### What Does Not Change

- `BaseLLMClient` interface (`complete(messages, system_prompt)` — unchanged)
- System prompt content (`prompts.py` — unchanged)
- Response parsing (`"NO"` vs interjection text — unchanged)
- Cooldown logic (now 15s, set in `config.yaml`)
- `SessionManager`, models, WebSocket, frontend — all unchanged

### Scope

Only `AgentLoop._build_context` is rewritten. Everything else is untouched.

---

## Implementation

### Files changed

**`backend/session/models.py`** — prerequisite fix.
All three model classes (`TranscriptChunk`, `FileDelta`, `Interjection`) use `datetime.utcnow` (naive) as their `timestamp` default factory. `SessionManager.start()` now uses `datetime.now(timezone.utc)` (aware). Computing `event.timestamp - snap.started_at` for elapsed-time rendering would crash with the same naive/aware mismatch fixed elsewhere. Fix: change all three `default_factory=datetime.utcnow` to `default_factory=lambda: datetime.now(timezone.utc)` and update the import.

**`backend/agent/loop.py`** — the core change.

`_build_context` will:
1. Pull `snap.transcript`, `snap.deltas`, `snap.interjections` from the session snapshot (full lists, not sliced)
2. Build a unified list of `(timestamp, label, content)` tuples
3. Sort by timestamp
4. Render each entry with elapsed `[MM:SS]` prefix — `FileDelta` entries show the filename (basename of path) and `(+N -N)` line counts in the header, followed by the full diff body
5. Return the assembled context string

---

## V2: Compaction (Out of Scope)

For very long sessions (45+ min), the growing timeline will eventually become large. A future compaction pass would:

1. Fire an async LLM call to summarize the timeline up to a cutoff point into a prose narrative
2. Capture a full snapshot of the current code file(s) as plain text (eliminating diff fragmentation — the model would see the whole file, not accumulated patches)
3. Replace the early timeline entries with the summary + code snapshot
4. Continue building the timeline from the cutoff point forward

This is explicitly deferred. At typical interview lengths the full timeline fits comfortably in current context windows.

---

## Non-Goals

- Multi-turn conversation thread (not needed — stateless calls with full context are equivalent given Codex CLI flattens messages to text anyway)
- Prompt caching (not available via Codex CLI subprocess; relevant if switching to OpenAI SDK or Anthropic directly)
- Frontend changes
- Changes to any other backend component
