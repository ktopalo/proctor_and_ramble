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
        padding: '8px 20px', borderRadius: 6, border: '1px solid #e5e7eb',
        background: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600,
      }}
    >
      Export transcript
    </button>
  )
}
