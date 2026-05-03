export interface TranscriptChunk {
  text: string
  timestamp: string
  duration_seconds: number
}

export interface FileDelta {
  path: string
  diff: string
  timestamp: string
}

export interface Interjection {
  text: string
  timestamp: string
  trigger: 'speech_pause' | 'file_save'
}

export interface InterviewPlan {
  problem_markdown: string
  follow_ups: string[]
  agent_briefing: string
  rubric: string
  source_url: string | null
}

export interface SessionSnapshot {
  transcript: TranscriptChunk[]
  deltas: FileDelta[]
  interjections: Interjection[]
  plan: InterviewPlan | null
  started_at: string | null
  ended_at: string | null
  watch_path: string | null
  revealed_follow_up_timestamps: string[]
}

export type WSEventType =
  | 'plan_loaded'
  | 'session_started'
  | 'session_ended'
  | 'transcript_chunk'
  | 'file_delta'
  | 'interjection'
  | 'follow_up_revealed'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}
