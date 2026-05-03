import type { Interjection } from '../types/session'
import { MarkdownText } from './MarkdownText'

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
            <MarkdownText style={{ color: 'rgba(255,255,255,0.95)', fontSize: 13 }}>
              {item.text}
            </MarkdownText>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 6, display: 'block' }}>
              {timeAgo(item.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
