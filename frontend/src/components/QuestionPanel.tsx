import type { InterviewPlan } from '../types/session'

interface Props {
  plan: InterviewPlan | null
}

export default function QuestionPanel({ plan }: Props) {
  if (!plan) {
    return (
      <div style={{ padding: 24, color: '#9ca3af' }}>
        No question loaded.
      </div>
    )
  }

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <h2 style={{ marginTop: 0, fontSize: 18 }}>Problem</h2>
      <p style={{ lineHeight: 1.6 }}>{plan.problem_statement}</p>

      {plan.constraints.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, color: '#6b7280', marginTop: 24 }}>CONSTRAINTS</h3>
          <ul style={{ paddingLeft: 20, lineHeight: 1.8 }}>
            {plan.constraints.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </>
      )}
    </div>
  )
}
