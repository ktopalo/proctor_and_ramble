# Glass UI Redesign + Timer + Question Preview
*2026-05-02*

## Summary

Redesign all frontend screens and components with an Apple-style dark glassmorphism aesthetic. Add two features: a configurable countdown timer (set on Setup, counts down during the interview) and an inline question preview on Setup with spoiler-protected sections.

---

## Design Token System

All components use a shared visual language defined as inline style constants:

| Token | Value |
|---|---|
| Body background | `linear-gradient(135deg, #1c1c3a 0%, #0d1b3e 60%, #0a2550 100%)` |
| Glass panel bg | `rgba(255, 255, 255, 0.07)` |
| Glass panel border | `1px solid rgba(255, 255, 255, 0.12)` |
| Glass panel blur | `backdrop-filter: blur(20px)` |
| Glass panel radius | `12px` |
| Glass card bg (nested) | `rgba(255, 255, 255, 0.04)` |
| Glass card border | `1px solid rgba(255, 255, 255, 0.08)` |
| Accent | `#60d0ff` |
| Accent bg | `rgba(96, 208, 255, 0.06)` |
| Accent border | `rgba(96, 208, 255, 0.18)` |
| Text primary | `rgba(255, 255, 255, 0.95)` |
| Text secondary | `rgba(255, 255, 255, 0.55)` |
| Text muted | `rgba(255, 255, 255, 0.35)` |
| Spoiler badge bg | `rgba(255, 200, 100, 0.15)` |
| Spoiler badge border | `rgba(255, 200, 100, 0.25)` |
| Spoiler badge text | `rgba(255, 200, 100, 0.7)` |
| Button primary bg | `rgba(255, 255, 255, 0.88)` |
| Button primary text | `#0d1b3e` |
| Font | `system-ui, -apple-system, sans-serif` |

---

## Files Changed

### `frontend/src/index.css`

Set body background gradient and remove default margin:

```css
body {
  margin: 0;
  background: linear-gradient(135deg, #1c1c3a 0%, #0d1b3e 60%, #0a2550 100%);
  min-height: 100vh;
  font-family: system-ui, -apple-system, sans-serif;
}
```

---

### `frontend/src/App.tsx`

Add `timerDuration` state (seconds). Thread it from Setup → Interview:

```tsx
const [screen, setScreen] = useState<Screen>('setup')
const [timerDuration, setTimerDuration] = useState<number>(45 * 60)

// Setup calls: onStart(durationSeconds)
// Interview receives: timerDuration={timerDuration}
```

---

### `frontend/src/components/Timer.tsx`

**New prop:** `durationSeconds?: number`

**Behaviour:**
- If `durationSeconds` is provided: countdown from `durationSeconds`. Display = `durationSeconds - elapsed`. If negative, show `-mm:ss` (overtime).
- If not provided: count up from 0 (existing behaviour).

**Color states (applied to the timer text):**
- Normal: `rgba(255, 255, 255, 0.95)`
- Amber: `#fbbf24` when remaining ≤ 300s (5 min)
- Red: `#f87171` when remaining ≤ 60s or overtime

**Display format:** `mm:ss` (no hours prefix unless ≥ 1h). Overtime prefixed with `-`.

---

### `frontend/src/screens/Setup.tsx`

Full glass redesign. Layout (top to bottom):

1. **Header** — centred title "Proctor & Ramble" + subtitle, no background panel
2. **Question URL section** — glass input + Load button. On success shows accent-coloured "✓ Loaded" badge inline.
3. **Question preview card** — appears after successful load, accent-bordered glass card:
   - Problem statement (always visible)
   - Constraints as pill tags (always visible)
   - Three collapsible accordions, each collapsed by default, each with amber "spoiler" badge:
     - Hints (count shown, e.g. "Hints (2)")
     - Expected approaches (count shown)
     - Rubric (dimension count shown)
   - Clicking a row toggles it open/closed. Chevron rotates `▸` → `▾`.
4. **Watch path + Duration row** — two inputs side by side (3:1 ratio). Duration is a number input (minutes), default 45. Stored as minutes in state, converted to seconds on Start.
5. **Start Interview button** — disabled until question loaded AND watch path filled. Full-width, primary button style.

**`onStart` signature change:** `onStart(durationSeconds: number) → void`

---

### `frontend/src/screens/Interview.tsx`

**New prop:** `timerDuration: number` (seconds)

Glass layout:

- **Header bar** — glass panel: title left, `<Timer startedAt={...} durationSeconds={timerDuration} />` centre, "End Interview" button right.
- **Main area** — flex row, no gap:
  - Left 60%: glass panel wrapping `<QuestionPanel />`
  - Right 40%: glass panel wrapping `<ProctorPanel />`
- **Status bar** — glass strip at bottom: connection dot + watch path.

---

### `frontend/src/screens/Feedback.tsx`

Glass redesign. Same layout as current (header + two-column content) but dark glass styled:

- Header: glass bar with "Interview Complete" title, Export + Get Feedback + New Interview buttons (glass style).
- Transcript panel (40%): glass panel, scrollable.
- Right column (60%): code diffs in glass panel + feedback section below when available.
- Code diff `<pre>` blocks: `rgba(0,0,0,0.3)` background, accent-tinted border.

---

### `frontend/src/components/QuestionPanel.tsx`

- Wrapper: full-height, overflow scroll, dark glass padding.
- "Problem" label: muted uppercase small caps.
- Problem statement: text primary, 1.6 line-height.
- Constraints: pill tags (glass card style).
- Empty state: muted text, centred.

---

### `frontend/src/components/ProctorPanel.tsx`

- Wrapper: full-height, overflow scroll.
- Empty state: "Proctor is watching..." muted + centred.
- Interjection cards: accent-tinted glass (`rgba(96,208,255,0.06)` bg, accent border). Text primary. Timestamp muted small below.

---

### `frontend/src/components/ExportButton.tsx`

Restyled to glass button: `rgba(255,255,255,0.1)` bg, white border, white text. No behaviour changes.

---

## Feature: Countdown Timer

**Setup:** Duration input (minutes, default 45). Converts to seconds before passing to `onStart`.

**Interview:** `Timer` receives `durationSeconds`. Counts down. At 0, goes negative (overtime). Color shifts amber → red as time runs low.

**No backend change required** — duration is frontend-only state.

---

## Feature: Question Preview with Spoilers

After `POST /question/load` succeeds, the plan is available via `snapshot.plan` from `useSession` (the backend broadcasts a `plan_loaded` WS event which the hook already handles). Setup reads `snapshot.plan` to render the preview — no extra fetch needed.

**Always visible:** `problem_statement`, `constraints`

**Spoiler-collapsed by default:** `hints`, `expected_approaches`, `rubric`

Each spoiler row shows a count ("Hints (2)"), an amber "spoiler" badge, and a chevron. Clicking expands the content. State is local to Setup (`useState<Record<string, boolean>>`).

---

## Out of Scope

- Dark/light mode toggle
- Animations or transitions beyond chevron rotation
- Backend changes
- Mobile responsiveness
