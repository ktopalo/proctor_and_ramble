import { useEffect, useState } from 'react'
import ExportButton from '../components/ExportButton'
import { useSession } from '../hooks/useSession'
import type { SessionSnapshot } from '../types/session'

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

  if (!snapshot) return <div style={{ padding: 24 }}>Loading...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid #e5e7eb',
      }}>
        <span style={{ fontWeight: 700, fontSize: 16 }}>Interview Complete</span>
        <div style={{ display: 'flex', gap: 12 }}>
          <ExportButton snapshot={snapshot} />
          <button
            onClick={handleGenerateFeedback}
            disabled={loadingFeedback}
            style={{ padding: '8px 20px', borderRadius: 6, border: 'none', background: '#0070f3', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
          >
            {loadingFeedback ? 'Generating...' : 'Get Feedback'}
          </button>
          <button
            onClick={onReset}
            style={{ padding: '8px 20px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}
          >
            New Interview
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Transcript */}
        <div style={{ flex: '0 0 40%', borderRight: '1px solid #e5e7eb', padding: 24, overflowY: 'auto' }}>
          <h3 style={{ marginTop: 0 }}>Transcript</h3>
          {snapshot.transcript.length === 0 ? (
            <p style={{ color: '#9ca3af' }}>No speech recorded.</p>
          ) : (
            snapshot.transcript.map((chunk, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(chunk.timestamp).toLocaleTimeString()}</span>
                <p style={{ margin: '4px 0', lineHeight: 1.6 }}>{chunk.text}</p>
              </div>
            ))
          )}
        </div>

        {/* Right column: code diffs + feedback */}
        <div style={{ flex: '0 0 60%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, padding: 24, overflowY: 'auto', borderBottom: '1px solid #e5e7eb' }}>
            <h3 style={{ marginTop: 0 }}>Code changes</h3>
            {snapshot.deltas.length === 0 ? (
              <p style={{ color: '#9ca3af' }}>No code changes recorded.</p>
            ) : (
              snapshot.deltas.map((delta, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(delta.timestamp).toLocaleTimeString()} — {delta.path}</span>
                  <pre style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: 12, fontSize: 12, overflowX: 'auto', marginTop: 4 }}>
                    {delta.diff}
                  </pre>
                </div>
              ))
            )}
          </div>

          {feedback && (
            <div style={{ padding: 24, overflowY: 'auto', maxHeight: '40%' }}>
              <h3 style={{ marginTop: 0 }}>Feedback</h3>
              <pre style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: 14 }}>{feedback}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
