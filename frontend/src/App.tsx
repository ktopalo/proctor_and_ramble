// frontend/src/App.tsx
import { useState } from 'react'
import Setup from './screens/Setup'
import Interview from './screens/Interview'
import Feedback from './screens/Feedback'

export type Screen = 'setup' | 'interview' | 'feedback'

export default function App() {
  const [screen, setScreen] = useState<Screen>('setup')

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {screen === 'setup' && <Setup onStart={() => setScreen('interview')} />}
      {screen === 'interview' && <Interview onEnd={() => setScreen('feedback')} />}
      {screen === 'feedback' && <Feedback onReset={() => setScreen('setup')} />}
    </div>
  )
}
