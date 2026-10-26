import { useEffect, useMemo, useRef } from 'react'

export function HtmlIframePreview({ html, title }: { html: string; title: string }) {
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
      } catch {
        el.style.height = '640px'
      }
    }

    iframe.addEventListener('load', resize)
    return () => iframe.removeEventListener('load', resize)
  }, [blobUrl])

  return (
    <iframe
      ref={iframeRef}
      title={title}
      src={blobUrl}
      sandbox=""
      className="w-full min-h-[480px] border-0 bg-zinc-100"
    />
  )
}
