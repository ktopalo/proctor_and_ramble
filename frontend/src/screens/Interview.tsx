// frontend/src/screens/Interview.tsx
import { useEffect, useState } from 'react'
import Timer from '../components/Timer'
import QuestionPanel from '../components/QuestionPanel'
import ProctorPanel from '../components/ProctorPanel'
import { useSession } from '../hooks/useSession'

interface Props {
  onEnd: () => void
  timerDuration: number
}

export default function Interview({ onEnd, timerDuration }: Props) {
  const { snapshot, connected, endSession, fetchSnapshot } = useSession()

  // Populate plan + session state that was set up during Setup screen
  useEffect(() => { fetchSnapshot() }, [])

  const handleEnd = async () => {
    await endSession()
    onEnd()
  }

  const [showSpeech, setShowSpeech] = useState(false)
  const recentSpeech = snapshot.transcript.slice(-10).reverse()

  const glassPanel = {
    background: 'rgba(255,255,255,0.07)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 12,
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
  } as const

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', padding: 16, gap: 12, boxSizing: 'border-box' }}>
      {/* Header */}
      <div style={{
        ...glassPanel,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px', flexShrink: 0,
      }}>
        <span style={{ color: 'rgba(255,255,255,0.95)', fontWeight: 700, fontSize: 15 }}>
          Proctor &amp; Ramble
        </span>
        <Timer startedAt={snapshot.started_at} durationSeconds={timerDuration} />
        <button
          onClick={handleEnd}
          style={{
            background: 'rgba(255,255,255,0.88)', color: '#0d1b3e', border: 'none',
            borderRadius: 8, padding: '7px 16px', fontWeight: 700, fontSize: 13, cursor: 'pointer',
          }}
        >
          End Interview
        </button>
      </div>

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, gap: 12, overflow: 'hidden' }}>
        <div style={{ ...glassPanel, flex: '0 0 60%', overflow: 'hidden' }}>
          <QuestionPanel plan={snapshot.plan} />
        </div>
        <div style={{ ...glassPanel, flex: '0 0 40%', overflow: 'hidden' }}>
          <ProctorPanel interjections={snapshot.interjections} />
        </div>
      </div>

      {/* Speech stream (collapsed by default) */}
      {showSpeech && (
        <div style={{
          ...glassPanel,
          padding: '10px 16px', flexShrink: 0, maxHeight: 150, overflowY: 'auto',
        }}>
          {recentSpeech.length === 0 ? (
            <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 12 }}>No speech detected yet...</span>
          ) : (
            recentSpeech.map((chunk, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, fontSize: 12, lineHeight: 1.7 }}>
                <span style={{ color: 'rgba(255,255,255,0.3)', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
                  {new Date(chunk.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span style={{ color: 'rgba(255,255,255,0.7)' }}>{chunk.text}</span>
              </div>
            ))
          )}
        </div>
      )}

      {/* Status bar */}
      <div style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 8,
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '8px 16px', fontSize: 12, flexShrink: 0,
      }}>
        <span style={{ color: connected ? '#34d399' : '#f87171' }}>
          {connected ? '● Recording' : '○ Disconnected'}
        </span>
        {snapshot.watch_path && (
          <span style={{ color: 'rgba(255,255,255,0.45)' }}>watching: {snapshot.watch_path}</span>
        )}
        <button
          onClick={() => setShowSpeech(v => !v)}
          style={{
            marginLeft: 'auto',
            background: 'none',
            border: 'none',
            color: 'rgba(255,255,255,0.35)',
            cursor: 'pointer',
            fontSize: 12,
            padding: '0 4px',
          }}
        >
          speech {showSpeech ? '▾' : '▸'}
        </button>
      </div>
    </div>
  )
}
