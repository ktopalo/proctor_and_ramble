// frontend/src/screens/Feedback.tsx
export default function Feedback({ onReset }: { onReset: () => void }) {
  return <div>Feedback <button onClick={onReset}>Reset</button></div>
}
