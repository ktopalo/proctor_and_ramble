import type { InterviewPlan } from '../types/session'
import { MarkdownText } from './MarkdownText'

interface Props {
  plan: InterviewPlan | null
}

export default function QuestionPanel({ plan }: Props) {
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
      <MarkdownText style={{ color: 'rgba(255,255,255,0.95)', fontSize: 14, marginBottom: 24 }}>
        {plan.problem_statement}
      </MarkdownText>

      {plan.constraints.length > 0 && (
        <>
          <div style={{
            color: 'rgba(255,255,255,0.35)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            fontWeight: 600,
            marginBottom: 10,
          }}>
            Constraints
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {plan.constraints.map((c, i) => (
              <span key={i} style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6,
                padding: '4px 10px',
                color: 'rgba(255,255,255,0.55)',
                fontSize: 12,
              }}>
                {c}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
