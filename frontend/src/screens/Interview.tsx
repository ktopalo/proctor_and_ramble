// frontend/src/screens/Interview.tsx
import { useEffect } from 'react'
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
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
        {snapshot.watch_path && (
          <span style={{ color: 'rgba(255,255,255,0.45)' }}>watching: {snapshot.watch_path}</span>
        )}
      </div>
    </div>
  )
}
