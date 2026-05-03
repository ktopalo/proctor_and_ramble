import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'

interface Props {
  children: string
  style?: React.CSSProperties
}

type C = { children?: ReactNode }

export function MarkdownText({ children, style }: Props) {
  return (
    <div style={{ lineHeight: 1.6, ...style }}>
      <ReactMarkdown
        components={{
          p: ({ children }: C) => (
            <p style={{ margin: '0 0 8px 0', color: 'inherit' }}>{children}</p>
          ),
          ul: ({ children }: C) => (
            <ul style={{ paddingLeft: 20, margin: '0 0 8px 0' }}>{children}</ul>
          ),
          ol: ({ children }: C) => (
            <ol style={{ paddingLeft: 20, margin: '0 0 8px 0' }}>{children}</ol>
          ),
          li: ({ children }: C) => (
            <li style={{ marginBottom: 4, color: 'inherit' }}>{children}</li>
          ),
          strong: ({ children }: C) => (
            <strong style={{ color: '#60d0ff', fontWeight: 600 }}>{children}</strong>
          ),
          em: ({ children }: C) => (
            <em style={{ color: 'rgba(255,255,255,0.8)' }}>{children}</em>
          ),
          code: ({ children }: C) => (
            <code style={{
              fontFamily: 'monospace',
              background: 'rgba(255,255,255,0.08)',
              padding: '1px 5px',
              borderRadius: 3,
              fontSize: '0.9em',
            }}>{children}</code>
          ),
          pre: ({ children }: C) => (
            <pre style={{
              background: 'rgba(255,255,255,0.05)',
              padding: 12,
              borderRadius: 6,
              overflowX: 'auto',
              margin: '0 0 8px 0',
            }}>{children}</pre>
          ),
          h1: ({ children }: C) => (
            <h1 style={{ fontSize: '1.1em', fontWeight: 600, margin: '0 0 8px 0', color: 'rgba(255,255,255,0.95)' }}>{children}</h1>
          ),
          h2: ({ children }: C) => (
            <h2 style={{ fontSize: '1em', fontWeight: 600, margin: '0 0 6px 0', color: 'rgba(255,255,255,0.9)' }}>{children}</h2>
          ),
          h3: ({ children }: C) => (
            <h3 style={{ fontSize: '0.95em', fontWeight: 600, margin: '0 0 6px 0', color: 'rgba(255,255,255,0.85)' }}>{children}</h3>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
