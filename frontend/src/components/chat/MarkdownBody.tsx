import type { ReactNode } from 'react'
import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { normalizeAgentMarkdown } from '../../lib/normalizeAgentMarkdown'

const mdComponents = {
  p: ({ children }: { children?: ReactNode }) => <p>{children}</p>,
  ul: ({ children }: { children?: ReactNode }) => <ul>{children}</ul>,
  ol: ({ children }: { children?: ReactNode }) => <ol>{children}</ol>,
  li: ({ children }: { children?: ReactNode }) => <li>{children}</li>,
  h1: ({ children }: { children?: ReactNode }) => <h1>{children}</h1>,
  h2: ({ children }: { children?: ReactNode }) => <h2>{children}</h2>,
  h3: ({ children }: { children?: ReactNode }) => <h3>{children}</h3>,
  h4: ({ children }: { children?: ReactNode }) => <h4>{children}</h4>,
  strong: ({ children }: { children?: ReactNode }) => <strong>{children}</strong>,
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a href={href} target="_blank" rel="noreferrer noopener" className="assistant-markdown-link">
      {children}
    </a>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => <blockquote>{children}</blockquote>,
  hr: () => <hr />,
  pre: ({ children }: { children?: ReactNode }) => <pre className="assistant-markdown-pre">{children}</pre>,
  code: ({ children, className }: { children?: ReactNode; className?: string }) => {
    const isBlock = className?.includes('language-')
    if (isBlock) return <code className={className}>{children}</code>
    return <code className="assistant-markdown-code">{children}</code>
  },
}

function AssistantMarkdown({ content, streaming }: { content: string; streaming?: boolean }) {
  const normalized = useMemo(() => normalizeAgentMarkdown(content), [content])

  return (
    <div className="assistant-markdown min-w-0">
      <ReactMarkdown components={mdComponents}>{normalized}</ReactMarkdown>
      {streaming && <span className="stream-cursor motion-reduce:hidden" aria-hidden />}
    </div>
  )
}

export function MarkdownBody({ content }: { content: string }) {
  return <AssistantMarkdown content={content} />
}

export function StreamingMarkdown({ content }: { content: string }) {
  return <AssistantMarkdown content={content} streaming />
}
