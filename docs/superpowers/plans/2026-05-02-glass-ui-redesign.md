# Glass UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all frontend screens/components with Apple dark glassmorphism, add a configurable countdown timer, and add an inline question preview with spoiler-protected sections on the Setup screen.

**Architecture:** Pure frontend changes — 9 files touched, no backend changes. All styling is inline (existing pattern). Shared design tokens are defined as local constants in each file. Timer duration threads from Setup → App → Interview as `durationSeconds: number`. Question preview reads from `snapshot.plan` (already populated by the existing WS `plan_loaded` event).

**Tech Stack:** React 18, TypeScript, Vite. Verify with `cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit` after each task.

---

## File Map

| File | Change |
|---|---|
| `frontend/src/index.css` | Replace Vite defaults with gradient background + input focus styles |
| `frontend/src/components/Timer.tsx` | Add `durationSeconds` prop, countdown logic, colour states |
| `frontend/src/components/QuestionPanel.tsx` | Glass restyle, constraints as pills |
| `frontend/src/components/ProctorPanel.tsx` | Glass restyle, accent-tinted interjection cards |
| `frontend/src/components/ExportButton.tsx` | Glass button restyle (no logic change) |
| `frontend/src/App.tsx` | Add `timerDuration` state, update `onStart` signature |
| `frontend/src/screens/Interview.tsx` | Accept `timerDuration` prop, glass layout |
| `frontend/src/screens/Setup.tsx` | Full glass redesign, duration input, question preview with spoilers |
| `frontend/src/screens/Feedback.tsx` | Glass layout restyle |

---

## Phase 1 — Foundation

### Task 1: Global styles

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace index.css entirely**

```css
*, *::before, *::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: linear-gradient(135deg, #1c1c3a 0%, #0d1b3e 60%, #0a2550 100%);
  min-height: 100vh;
  font-family: system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#root {
  height: 100vh;
}

input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

input:focus {
  outline: none;
  border-color: rgba(96, 208, 255, 0.4) !important;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: dark glass global styles"
```

---

### Task 2: Timer — countdown + colour states

**Files:**
- Modify: `frontend/src/components/Timer.tsx`

- [ ] **Step 1: Replace Timer.tsx**

```tsx
import { useEffect, useState } from 'react'

interface Props {
  startedAt: string | null
  durationSeconds?: number
}

function formatTime(totalSeconds: number): string {
  const abs = Math.abs(totalSeconds)
  const h = Math.floor(abs / 3600)
  const m = Math.floor((abs % 3600) / 60)
  const s = abs % 60
  const sign = totalSeconds < 0 ? '-' : ''
  if (h > 0) return `${sign}${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${sign}${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function timerColour(remaining: number | null): string {
  if (remaining === null) return 'rgba(255,255,255,0.95)'
  if (remaining <= 60) return '#f87171'
  if (remaining <= 300) return '#fbbf24'
  return 'rgba(255,255,255,0.95)'
}

export default function Timer({ startedAt, durationSeconds }: Props) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt).getTime()
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [startedAt])

  const remaining = durationSeconds !== undefined ? durationSeconds - elapsed : null
  const display = remaining !== null ? remaining : elapsed

  return (
    <span style={{
      fontVariantNumeric: 'tabular-nums',
      fontWeight: 700,
      fontSize: 18,
      color: timerColour(remaining),
      letterSpacing: '0.02em',
    }}>
      ⏱ {formatTime(display)}
    </span>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Timer.tsx
git commit -m "feat: Timer countdown mode with amber/red colour states"
```

---

## Phase 2 — Components

### Task 3: QuestionPanel glass restyle

**Files:**
- Modify: `frontend/src/components/QuestionPanel.tsx`

- [ ] **Step 1: Replace QuestionPanel.tsx**

```tsx
import type { InterviewPlan } from '../types/session'

interface Props {
  plan: InterviewPlan | null
}

export default function QuestionPanel({ plan }: Props) {
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
      <p style={{ color: 'rgba(255,255,255,0.95)', lineHeight: 1.7, margin: '0 0 24px', fontSize: 14 }}>
        {plan.problem_statement}
      </p>

      {plan.constraints.length > 0 && (
        <>
          <div style={{
            color: 'rgba(255,255,255,0.35)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            fontWeight: 600,
            marginBottom: 10,
          }}>
            Constraints
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {plan.constraints.map((c, i) => (
              <span key={i} style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6,
                padding: '4px 10px',
                color: 'rgba(255,255,255,0.55)',
                fontSize: 12,
              }}>
                {c}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/QuestionPanel.tsx
git commit -m "feat: QuestionPanel glass restyle with constraint pills"
```

---

### Task 4: ProctorPanel glass restyle

**Files:**
- Modify: `frontend/src/components/ProctorPanel.tsx`

- [ ] **Step 1: Replace ProctorPanel.tsx**

```tsx
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
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.25)',
        fontSize: 14,
      }}>
        Proctor is watching...
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
        marginBottom: 16,
      }}>
        Proctor
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {interjections.map((item, i) => (
          <div key={i} style={{
            background: 'rgba(96,208,255,0.06)',
            border: '1px solid rgba(96,208,255,0.18)',
            borderRadius: 10,
            padding: '12px 16px',
          }}>
            <p style={{ margin: 0, lineHeight: 1.6, color: 'rgba(255,255,255,0.95)', fontSize: 13 }}>
              {item.text}
            </p>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 6, display: 'block' }}>
              {timeAgo(item.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProctorPanel.tsx
git commit -m "feat: ProctorPanel glass restyle with accent interjection cards"
```

---

### Task 5: ExportButton glass restyle

**Files:**
- Modify: `frontend/src/components/ExportButton.tsx`

- [ ] **Step 1: Replace only the button's style in ExportButton.tsx**

Read the file first, then replace just the `<button>` element's style. The `buildInterleaved` function and `handleExport` logic are unchanged. The full file:

```tsx
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
        padding: '8px 20px',
        borderRadius: 8,
        border: '1px solid rgba(255,255,255,0.15)',
        background: 'rgba(255,255,255,0.07)',
        color: 'rgba(255,255,255,0.7)',
        cursor: 'pointer',
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      Export transcript
    </button>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ExportButton.tsx
git commit -m "feat: ExportButton glass restyle"
```

---

## Phase 3 — Screens

### Task 6: App.tsx + Interview.tsx — timer threading

These two files are coupled by the `timerDuration` prop and must be updated together.

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/screens/Interview.tsx`

- [ ] **Step 1: Replace App.tsx**

```tsx
import { useState } from 'react'
import Setup from './screens/Setup'
import Interview from './screens/Interview'
import Feedback from './screens/Feedback'

export type Screen = 'setup' | 'interview' | 'feedback'

export default function App() {
  const [screen, setScreen] = useState<Screen>('setup')
  const [timerDuration, setTimerDuration] = useState<number>(45 * 60)

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {screen === 'setup' && (
        <Setup onStart={(durationSeconds) => {
          setTimerDuration(durationSeconds)
          setScreen('interview')
        }} />
      )}
      {screen === 'interview' && (
        <Interview timerDuration={timerDuration} onEnd={() => setScreen('feedback')} />
      )}
      {screen === 'feedback' && <Feedback onReset={() => setScreen('setup')} />}
    </div>
  )
}
```

- [ ] **Step 2: Replace Interview.tsx**

```tsx
import { useEffect } from 'react'
import Timer from '../components/Timer'
import QuestionPanel from '../components/QuestionPanel'
import ProctorPanel from '../components/ProctorPanel'
import { useSession } from '../hooks/useSession'

const GLASS = {
  background: 'rgba(255,255,255,0.07)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.12)',
} as const

interface Props {
  onEnd: () => void
  timerDuration: number
}

export default function Interview({ onEnd, timerDuration }: Props) {
  const { snapshot, connected, endSession, fetchSnapshot } = useSession()

  useEffect(() => { fetchSnapshot() }, [])

  const handleEnd = async () => {
    await endSession()
    onEnd()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        ...GLASS,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 24px', flexShrink: 0,
        borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderRight: 'none',
      }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: 'rgba(255,255,255,0.9)' }}>
          Proctor & Ramble
        </span>
        <Timer startedAt={snapshot.started_at} durationSeconds={timerDuration} />
        <button
          onClick={handleEnd}
          style={{
            padding: '7px 18px', borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.15)',
            background: 'rgba(255,255,255,0.07)',
            color: 'rgba(255,255,255,0.7)',
            cursor: 'pointer', fontSize: 13,
          }}
        >
          End Interview
        </button>
      </div>

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          ...GLASS,
          flex: '0 0 60%',
          borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderBottom: 'none',
          overflow: 'hidden',
        }}>
          <QuestionPanel plan={snapshot.plan} />
        </div>
        <div style={{
          ...GLASS,
          flex: '0 0 40%',
          borderRadius: 0, borderTop: 'none', borderRight: 'none', borderBottom: 'none',
          overflow: 'hidden',
        }}>
          <ProctorPanel interjections={snapshot.interjections} />
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        ...GLASS,
        padding: '8px 24px', fontSize: 12,
        display: 'flex', gap: 16, flexShrink: 0, alignItems: 'center',
        borderRadius: 0, borderLeft: 'none', borderRight: 'none', borderBottom: 'none',
      }}>
        <span style={{ color: connected ? '#4ade80' : '#f87171' }}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
        {snapshot.watch_path && (
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>watching: {snapshot.watch_path}</span>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/screens/Interview.tsx
git commit -m "feat: thread timerDuration from App through Interview to Timer"
```

---

### Task 7: Setup screen — full redesign + question preview + spoilers

This is the largest task. Read the existing Setup.tsx first, then replace it entirely.

**Files:**
- Modify: `frontend/src/screens/Setup.tsx`

- [ ] **Step 1: Replace Setup.tsx**

```tsx
import { useState } from 'react'
import type { ReactNode } from 'react'
import { useSession } from '../hooks/useSession'
import type { InterviewPlan } from '../types/session'

interface Props {
  onStart: (durationSeconds: number) => void
}

const GLASS_INPUT = {
  padding: '10px 14px',
  fontSize: 13,
  background: 'rgba(255,255,255,0.07)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8,
  color: 'rgba(255,255,255,0.9)',
  width: '100%',
} as const

const LABEL = {
  color: 'rgba(255,255,255,0.45)',
  fontSize: 10,
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '1.5px',
  marginBottom: 6,
  display: 'block',
} as const

function SpoilerRow({
  label,
  count,
  open,
  onToggle,
  children,
}: {
  label: string
  count: number
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 8 }}>
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          paddingBottom: open ? 8 : 0,
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            background: 'rgba(255,200,100,0.15)',
            border: '1px solid rgba(255,200,100,0.25)',
            borderRadius: 4,
            padding: '1px 6px',
            color: 'rgba(255,200,100,0.7)',
            fontSize: 9,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>spoiler</span>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
            {label} ({count})
          </span>
        </div>
        <span style={{
          color: 'rgba(255,255,255,0.3)',
          fontSize: 11,
          display: 'inline-block',
          transform: open ? 'rotate(90deg)' : 'none',
          transition: 'transform 0.15s',
        }}>▸</span>
      </div>
      {open && (
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 8,
          padding: '10px 12px',
        }}>
          {children}
        </div>
      )}
    </div>
  )
}

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
      <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, lineHeight: 1.6, margin: '0 0 12px' }}>
        {plan.problem_statement}
      </p>
      {plan.constraints.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 12 }}>
          {plan.constraints.map((c, i) => (
            <span key={i} style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 4,
              padding: '3px 8px',
              color: 'rgba(255,255,255,0.45)',
              fontSize: 11,
            }}>{c}</span>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <SpoilerRow
          label="Hints"
          count={plan.hints.length}
          open={!!open.hints}
          onToggle={() => toggle('hints')}
        >
          <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
            {plan.hints.map((h, i) => (
              <li key={i} style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, lineHeight: 1.6 }}>
                {h.text}
              </li>
            ))}
          </ul>
        </SpoilerRow>
        <SpoilerRow
          label="Expected approaches"
          count={plan.expected_approaches.length}
          open={!!open.approaches}
          onToggle={() => toggle('approaches')}
        >
          <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
            {plan.expected_approaches.map((a, i) => (
              <li key={i} style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, lineHeight: 1.6 }}>{a}</li>
            ))}
          </ul>
        </SpoilerRow>
        <SpoilerRow
          label="Rubric"
          count={Object.keys(plan.rubric).length}
          open={!!open.rubric}
          onToggle={() => toggle('rubric')}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {Object.entries(plan.rubric).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', gap: 10 }}>
                <span style={{
                  color: 'rgba(255,255,255,0.55)',
                  fontSize: 12,
                  minWidth: 110,
                  textTransform: 'capitalize',
                }}>{k}</span>
                <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>{v}</span>
              </div>
            ))}
          </div>
        </SpoilerRow>
      </div>
    </div>
  )
}

export default function Setup({ onStart }: Props) {
  const [url, setUrl] = useState('')
  const [watchPath, setWatchPath] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(45)
  const [loading, setLoading] = useState(false)
  const [planLoaded, setPlanLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { snapshot, loadQuestion, startSession } = useSession()

  const handleLoadQuestion = async () => {
    if (!url) return
    setLoading(true)
    setError(null)
    try {
      await loadQuestion(url)
      setPlanLoaded(true)
    } catch {
      setError('Failed to load question. Check the URL and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!watchPath || !planLoaded) return
    setLoading(true)
    try {
      await startSession(watchPath)
      onStart(durationMinutes * 60)
    } catch {
      setError('Failed to start session.')
      setLoading(false)
    }
  }

  const canStart = planLoaded && watchPath.length > 0 && !loading

  return (
    <div style={{
      maxWidth: 560,
      margin: '60px auto',
      padding: '0 24px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 36 }}>
        <h1 style={{
          color: 'rgba(255,255,255,0.95)',
          margin: '0 0 6px',
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: '-0.5px',
        }}>
          Proctor & Ramble
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.35)', margin: 0, fontSize: 13 }}>
          AI-powered technical interview proctor
        </p>
      </div>

      {/* URL input */}
      <div style={{ marginBottom: 16 }}>
        <label style={LABEL}>Interview question URL</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLoadQuestion()}
            placeholder="https://leetcode.com/problems/two-sum/"
            style={GLASS_INPUT}
          />
          <button
            onClick={handleLoadQuestion}
            disabled={!url || loading}
            style={{
              padding: '10px 16px',
              borderRadius: 8,
              border: 'none',
              background: planLoaded ? 'rgba(96,208,255,0.15)' : 'rgba(255,255,255,0.88)',
              color: planLoaded ? '#60d0ff' : '#0d1b3e',
              fontWeight: 700,
              fontSize: 13,
              cursor: !url || loading ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
              opacity: !url || (loading && !planLoaded) ? 0.6 : 1,
              flexShrink: 0,
            }}
          >
            {loading && !planLoaded ? '...' : planLoaded ? '✓ Loaded' : 'Load'}
          </button>
        </div>
      </div>

      {/* Question preview */}
      {planLoaded && snapshot.plan && <QuestionPreview plan={snapshot.plan} />}

      {/* Watch path + duration */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 10, marginBottom: 16 }}>
        <div>
          <label style={LABEL}>Watch path (file or folder)</label>
          <input
            type="text"
            value={watchPath}
            onChange={e => setWatchPath(e.target.value)}
            placeholder="/Users/you/projects/solution.py"
            style={GLASS_INPUT}
          />
        </div>
        <div>
          <label style={LABEL}>Duration (min)</label>
          <input
            type="number"
            value={durationMinutes}
            onChange={e => setDurationMinutes(Math.max(1, Number(e.target.value)))}
            min={1}
            style={{ ...GLASS_INPUT, textAlign: 'center' }}
          />
        </div>
      </div>

      {error && (
        <p style={{ color: '#f87171', fontSize: 12, marginBottom: 14, margin: '0 0 14px' }}>{error}</p>
      )}

      <button
        onClick={handleStart}
        disabled={!canStart}
        style={{
          width: '100%',
          padding: 14,
          fontSize: 15,
          fontWeight: 700,
          background: canStart ? 'rgba(255,255,255,0.88)' : 'rgba(255,255,255,0.06)',
          color: canStart ? '#0d1b3e' : 'rgba(255,255,255,0.2)',
          border: 'none',
          borderRadius: 10,
          cursor: canStart ? 'pointer' : 'not-allowed',
          letterSpacing: '-0.2px',
        }}
      >
        Start Interview
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/screens/Setup.tsx
git commit -m "feat: Setup screen glass redesign with question preview and spoiler accordions"
```

---

### Task 8: Feedback screen glass restyle

**Files:**
- Modify: `frontend/src/screens/Feedback.tsx`

- [ ] **Step 1: Replace Feedback.tsx**

```tsx
import { useEffect, useState } from 'react'
import ExportButton from '../components/ExportButton'
import { useSession } from '../hooks/useSession'
import type { SessionSnapshot } from '../types/session'

const GLASS = {
  background: 'rgba(255,255,255,0.07)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.12)',
} as const

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

  if (!snapshot) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.4)',
        fontSize: 14,
      }}>
        Loading...
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        ...GLASS,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 24px', flexShrink: 0,
        borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderRight: 'none',
      }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: 'rgba(255,255,255,0.9)' }}>
          Interview Complete
        </span>
        <div style={{ display: 'flex', gap: 10 }}>
          <ExportButton snapshot={snapshot} />
          <button
            onClick={handleGenerateFeedback}
            disabled={loadingFeedback}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: 'rgba(96,208,255,0.15)',
              color: '#60d0ff', cursor: loadingFeedback ? 'not-allowed' : 'pointer',
              fontWeight: 600, fontSize: 13,
              opacity: loadingFeedback ? 0.5 : 1,
            }}
          >
            {loadingFeedback ? 'Generating...' : 'Get Feedback'}
          </button>
          <button
            onClick={onReset}
            style={{
              padding: '8px 20px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.07)',
              color: 'rgba(255,255,255,0.6)', cursor: 'pointer', fontSize: 13,
            }}
          >
            New Interview
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Transcript */}
        <div style={{
          ...GLASS,
          flex: '0 0 40%', padding: 24, overflowY: 'auto',
          borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderBottom: 'none',
          boxSizing: 'border-box',
        }}>
          <div style={{
            color: 'rgba(255,255,255,0.35)', fontSize: 10,
            textTransform: 'uppercase', letterSpacing: '1.5px',
            fontWeight: 600, marginBottom: 16,
          }}>
            Transcript
          </div>
          {snapshot.transcript.length === 0 ? (
            <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: 13 }}>No speech recorded.</p>
          ) : (
            snapshot.transcript.map((chunk, i) => (
              <div key={i} style={{ marginBottom: 14 }}>
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)' }}>
                  {new Date(chunk.timestamp).toLocaleTimeString()}
                </span>
                <p style={{ margin: '4px 0 0', lineHeight: 1.6, color: 'rgba(255,255,255,0.8)', fontSize: 13 }}>
                  {chunk.text}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Right: diffs + feedback */}
        <div style={{ flex: '0 0 60%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{
            ...GLASS,
            flex: 1, padding: 24, overflowY: 'auto',
            borderRadius: 0, borderTop: 'none', borderRight: 'none',
            borderBottom: feedback ? undefined : 'none',
            boxSizing: 'border-box',
          }}>
            <div style={{
              color: 'rgba(255,255,255,0.35)', fontSize: 10,
              textTransform: 'uppercase', letterSpacing: '1.5px',
              fontWeight: 600, marginBottom: 16,
            }}>
              Code changes
            </div>
            {snapshot.deltas.length === 0 ? (
              <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: 13 }}>No code changes recorded.</p>
            ) : (
              snapshot.deltas.map((delta, i) => (
                <div key={i} style={{ marginBottom: 18 }}>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)' }}>
                    {new Date(delta.timestamp).toLocaleTimeString()} — {delta.path}
                  </span>
                  <pre style={{
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid rgba(96,208,255,0.12)',
                    borderRadius: 8, padding: 12, fontSize: 12,
                    overflowX: 'auto', marginTop: 6,
                    color: 'rgba(255,255,255,0.7)',
                  }}>
                    {delta.diff}
                  </pre>
                </div>
              ))
            )}
          </div>

          {feedback && (
            <div style={{
              ...GLASS,
              padding: 24, overflowY: 'auto', maxHeight: '40%',
              borderRadius: 0, borderRight: 'none', borderBottom: 'none',
              boxSizing: 'border-box',
            }}>
              <div style={{
                color: 'rgba(255,255,255,0.35)', fontSize: 10,
                textTransform: 'uppercase', letterSpacing: '1.5px',
                fontWeight: 600, marginBottom: 12,
              }}>
                Feedback
              </div>
              <pre style={{
                whiteSpace: 'pre-wrap', lineHeight: 1.7,
                fontSize: 13, color: 'rgba(255,255,255,0.8)', margin: 0,
              }}>
                {feedback}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/screens/Feedback.tsx
git commit -m "feat: Feedback screen glass restyle"
```

---

## Phase 4 — Final Verification

### Task 9: Full TypeScript check + build verify

**Files:** none

- [ ] **Step 1: Run full tsc**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npx tsc --noEmit
```

Expected: no errors across all files.

- [ ] **Step 2: Run Vite build**

```bash
cd frontend && PATH="/opt/homebrew/bin:$PATH" npm run build
```

Expected: build succeeds, no errors.

- [ ] **Step 3: Run backend tests to confirm nothing broken**

```bash
cd .. && source .venv/bin/activate && pytest -v
```

Expected: 35 passed.
