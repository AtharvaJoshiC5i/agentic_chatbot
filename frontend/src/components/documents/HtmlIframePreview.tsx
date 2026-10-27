import { useEffect, useMemo, useRef } from 'react'
import { focusDocumentPassage } from '../../lib/focusDocumentPassage'

export function HtmlIframePreview({ html, title, passage }: { html: string; title: string; passage?: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const blobUrl = useMemo(() => {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    return URL.createObjectURL(blob)
  }, [html])

  useEffect(() => {
    return () => URL.revokeObjectURL(blobUrl)
  }, [blobUrl])

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    function resize() {
      const el = iframeRef.current
      if (!el) return
      try {
        const doc = el.contentDocument
        if (!doc) return
        const height = Math.max(
          doc.documentElement?.scrollHeight ?? 0,
          doc.body?.scrollHeight ?? 0,
          480,
        )
        el.style.height = `${height + 8}px`
        if (passage && doc.body) focusDocumentPassage(doc.body, passage)
      } catch {
        el.style.height = '640px'
      }
    }

    iframe.addEventListener('load', resize)
    return () => iframe.removeEventListener('load', resize)
  }, [blobUrl, passage])

  return (
    <iframe
      ref={iframeRef}
      title={title}
      src={blobUrl}
      sandbox="allow-same-origin"
      className="w-full min-h-[480px] border-0 bg-zinc-100"
    />
  )
}
