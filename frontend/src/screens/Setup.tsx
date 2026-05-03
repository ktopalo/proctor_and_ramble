import { useState } from 'react'
import type { ReactNode } from 'react'
import { useSession } from '../hooks/useSession'
import type { InterviewPlan } from '../types/session'
import { Spinner } from '../components/Spinner'
import { MarkdownText } from '../components/MarkdownText'

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
            {loading && !planLoaded ? <Spinner /> : planLoaded ? '✓ Loaded' : 'Load'}
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
        <p style={{ color: '#f87171', fontSize: 12, margin: '0 0 14px' }}>{error}</p>
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
