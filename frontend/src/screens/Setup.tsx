import { useState } from 'react'
import { useSession } from '../hooks/useSession'

interface Props {
  onStart: (durationSeconds: number) => void
}

export default function Setup({ onStart }: Props) {
  const [url, setUrl] = useState('')
  const [watchPath, setWatchPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [planLoaded, setPlanLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { loadQuestion, startSession } = useSession()

  const handleLoadQuestion = async () => {
    if (!url) return
    setLoading(true)
    setError(null)
    try {
      await loadQuestion(url)
      setPlanLoaded(true)
    } catch (e) {
      setError('Failed to load question. Check the URL and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!watchPath) return
    setLoading(true)
    try {
      await startSession(watchPath)
      onStart(45 * 60)
    } catch (e) {
      setError('Failed to start session.')
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 560, margin: '80px auto', padding: '0 24px' }}>
      <h1 style={{ marginBottom: 8 }}>Proctor & Ramble</h1>
      <p style={{ color: '#666', marginBottom: 40 }}>AI-powered technical interview proctor</p>

      <section style={{ marginBottom: 32 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
          Interview question URL
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://leetcode.com/problems/two-sum/"
            style={{ flex: 1, padding: '8px 12px', fontSize: 14, border: '1px solid #ccc', borderRadius: 6 }}
            onKeyDown={(e) => e.key === 'Enter' && handleLoadQuestion()}
          />
          <button
            onClick={handleLoadQuestion}
            disabled={!url || loading}
            style={{ padding: '8px 16px', cursor: 'pointer', borderRadius: 6, border: 'none', background: '#0070f3', color: '#fff', fontWeight: 600 }}
          >
            {loading ? '...' : 'Load'}
          </button>
        </div>
        {planLoaded && <p style={{ color: '#16a34a', marginTop: 8, fontSize: 13 }}>✓ Question loaded</p>}
      </section>

      <section style={{ marginBottom: 32 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
          Watch path (file or folder)
        </label>
        <input
          type="text"
          value={watchPath}
          onChange={(e) => setWatchPath(e.target.value)}
          placeholder="/Users/you/projects/solution.py"
          style={{ width: '100%', padding: '8px 12px', fontSize: 14, border: '1px solid #ccc', borderRadius: 6, boxSizing: 'border-box' }}
        />
      </section>

      {error && <p style={{ color: '#dc2626', marginBottom: 16, fontSize: 13 }}>{error}</p>}

      <button
        onClick={handleStart}
        disabled={!planLoaded || !watchPath || loading}
        style={{
          width: '100%', padding: '12px', fontSize: 16, fontWeight: 700,
          background: planLoaded && watchPath ? '#111' : '#e5e7eb',
          color: planLoaded && watchPath ? '#fff' : '#9ca3af',
          border: 'none', borderRadius: 8, cursor: planLoaded && watchPath ? 'pointer' : 'not-allowed',
        }}
      >
        Start Interview
      </button>
    </div>
  )
}
