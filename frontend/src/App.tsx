// frontend/src/App.tsx
import { useState } from 'react'
import Setup from './screens/Setup'
import Interview from './screens/Interview'
import Feedback from './screens/Feedback'

export type Screen = 'setup' | 'interview' | 'feedback'

export default function App() {
  const [screen, setScreen] = useState<Screen>('setup')
  const [timerDuration, setTimerDuration] = useState<number>(45 * 60)

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {screen === 'setup' && <Setup onStart={(durationSeconds) => { setTimerDuration(durationSeconds); setScreen('interview') }} />}
      {screen === 'interview' && <Interview onEnd={() => setScreen('feedback')} timerDuration={timerDuration} />}
      {screen === 'feedback' && <Feedback onReset={() => setScreen('setup')} />}
    </div>
  )
}
