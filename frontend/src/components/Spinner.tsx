const style = `
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner { animation: spin 0.7s linear infinite; }
`

export function Spinner() {
  return (
    <>
      <style>{style}</style>
      <svg className="spinner" width="14" height="14" viewBox="0 0 14 14" fill="none">
        <circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.3)" strokeWidth="2"/>
        <path d="M7 2 A5 5 0 0 1 12 7" stroke="white" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    </>
  )
}
