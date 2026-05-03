import { useEffect, useRef, useState, useCallback } from 'react'
import type { SessionSnapshot, WSEvent, Interjection, InterviewPlan } from '../types/session'

const WS_URL = 'ws://127.0.0.1:8000/ws'

const EMPTY_SNAPSHOT: SessionSnapshot = {
  transcript: [],
  deltas: [],
  interjections: [],
  plan: null,
  started_at: null,
  ended_at: null,
  watch_path: null,
}

export function useSession() {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>(EMPTY_SNAPSHOT)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)

    ws.onmessage = (event) => {
      const msg: WSEvent = JSON.parse(event.data as string) as WSEvent
      setSnapshot((prev) => {
        switch (msg.type) {
          case 'plan_loaded':
            return { ...prev, plan: msg.data as unknown as InterviewPlan }
          case 'session_started':
            return { ...prev, started_at: new Date().toISOString() }
          case 'session_ended':
            return { ...prev, ended_at: new Date().toISOString() }
          case 'interjection':
            return {
              ...prev,
              interjections: [msg.data as unknown as Interjection, ...prev.interjections],
            }
          default:
            return prev
        }
      })
    }

    return () => ws.close()
  }, [])

  const loadQuestion = useCallback(async (url: string) => {
    const res = await fetch('/question/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!res.ok) throw new Error('Failed to load question')
    return res.json() as Promise<unknown>
  }, [])

  const startSession = useCallback(async (watchPath: string) => {
    const res = await fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watch_path: watchPath }),
    })
    if (!res.ok) throw new Error('Failed to start session')
  }, [])

  const endSession = useCallback(async () => {
    await fetch('/session/end', { method: 'POST' })
  }, [])

  const fetchSnapshot = useCallback(async () => {
    const res = await fetch('/session/snapshot')
    const data: SessionSnapshot = await res.json() as SessionSnapshot
    setSnapshot(data)
    return data
  }, [])

  return { snapshot, connected, loadQuestion, startSession, endSession, fetchSnapshot }
}
