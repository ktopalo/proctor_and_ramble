import { MarkdownText } from './MarkdownText'
import type { InterviewPlan } from '../types/session'

interface Props {
  plan: InterviewPlan | null
  revealedCount: number
}

export default function QuestionPanel({ plan, revealedCount }: Props) {
  if (!plan) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.25)',
        fontSize: 14,
      }}>
        No question loaded.
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
        marginBottom: 12,
      }}>
        Problem
      </div>
      <MarkdownText style={{ color: 'rgba(255,255,255,0.95)', fontSize: 14 }}>
        {plan.problem_markdown}
      </MarkdownText>

      {plan.follow_ups.slice(0, revealedCount).map((followUp, i) => (
        <div key={i} style={{
          marginTop: 24,
          paddingLeft: 16,
          borderLeft: '2px solid rgba(96,208,255,0.3)',
        }}>
          <div style={{
            color: 'rgba(96,208,255,0.6)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            fontWeight: 600,
            marginBottom: 8,
          }}>
            Follow-up {i + 1}
          </div>
          <MarkdownText style={{ color: 'rgba(255,255,255,0.85)', fontSize: 14 }}>
            {followUp}
          </MarkdownText>
        </div>
      ))}
    </div>
  )
}
