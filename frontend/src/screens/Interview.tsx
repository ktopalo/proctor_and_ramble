// frontend/src/screens/Interview.tsx
import { useEffect } from 'react'
import Timer from '../components/Timer'
import QuestionPanel from '../components/QuestionPanel'
import ProctorPanel from '../components/ProctorPanel'
import { useSession } from '../hooks/useSession'

interface Props {
  onEnd: () => void
}

export default function Interview({ onEnd }: Props) {
  const { snapshot, connected, endSession, fetchSnapshot } = useSession()

  // Populate plan + session state that was set up during Setup screen
  useEffect(() => { fetchSnapshot() }, [])

  const handleEnd = async () => {
    await endSession()
    onEnd()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid #e5e7eb', flexShrink: 0,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16 }}>Proctor & Ramble</span>
        <Timer startedAt={snapshot.started_at} />
        <button
          onClick={handleEnd}
          style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #e5e7eb',
            background: '#fff', cursor: 'pointer', fontSize: 14,
          }}
        >
          End Interview
        </button>
      </div>

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: '0 0 60%', borderRight: '1px solid #e5e7eb', overflow: 'hidden' }}>
          <QuestionPanel plan={snapshot.plan} />
        </div>
        <div style={{ flex: '0 0 40%', overflow: 'hidden' }}>
          <ProctorPanel interjections={snapshot.interjections} />
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        padding: '8px 24px', borderTop: '1px solid #e5e7eb', fontSize: 12,
        color: '#6b7280', display: 'flex', gap: 16, flexShrink: 0,
      }}>
        <span style={{ color: connected ? '#16a34a' : '#dc2626' }}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
        {snapshot.watch_path && <span>watching: {snapshot.watch_path}</span>}
      </div>
    </div>
  )
}
