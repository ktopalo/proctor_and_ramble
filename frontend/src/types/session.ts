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

export interface HintStep {
  level: number
  text: string
}

export interface InterviewPlan {
  problem_statement: string
  constraints: string[]
  hints: HintStep[]
  expected_approaches: string[]
  follow_up_questions: string[]
  rubric: Record<string, string>
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
}

export type WSEventType =
  | 'plan_loaded'
  | 'session_started'
  | 'session_ended'
  | 'transcript_chunk'
  | 'file_delta'
  | 'interjection'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}
