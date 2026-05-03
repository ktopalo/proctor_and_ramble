import { useEffect, useState } from 'react'
import ExportButton from '../components/ExportButton'
import { MarkdownText } from '../components/MarkdownText'
import { useSession } from '../hooks/useSession'
import type { SessionSnapshot } from '../types/session'

const GLASS = {
  background: 'rgba(255,255,255,0.07)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
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
        {/* Transcript — 40% */}
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

        {/* Right: diffs + feedback — 60% */}
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
              <MarkdownText style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)' }}>
                {feedback}
              </MarkdownText>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
