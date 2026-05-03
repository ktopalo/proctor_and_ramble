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
      <div style={{ padding: 24, color: '#9ca3af', fontSize: 14 }}>
        Proctor is watching...
      </div>
    )
  }

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <h2 style={{ marginTop: 0, fontSize: 18 }}>Proctor</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {interjections.map((item, i) => (
          <div
            key={i}
            style={{
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '12px 16px',
            }}
          >
            <p style={{ margin: 0, lineHeight: 1.6 }}>{item.text}</p>
            <span style={{ fontSize: 11, color: '#9ca3af', marginTop: 6, display: 'block' }}>
              {timeAgo(item.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
