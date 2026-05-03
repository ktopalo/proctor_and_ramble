// frontend/src/screens/Interview.tsx
export default function Interview({ onEnd }: { onEnd: () => void }) {
  return <div>Interview <button onClick={onEnd}>End</button></div>
}
