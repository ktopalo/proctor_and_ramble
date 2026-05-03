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
