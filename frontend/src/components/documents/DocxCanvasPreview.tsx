import { renderAsync } from 'docx-preview'
import { useEffect, useState } from 'react'
import { fetchDocumentBlob, fetchDocumentHtmlPreview } from '../../lib/documentFile'
import { HtmlIframePreview } from './HtmlIframePreview'

export function DocxCanvasPreview({
  documentId,
  filename,
}: {
  documentId: number
  filename: string
}) {
  const [host, setHost] = useState<HTMLDivElement | null>(null)
  const [useServerHtml, setUseServerHtml] = useState(false)
  const [serverHtml, setServerHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (useServerHtml) return
    if (!host) return

    let cancelled = false
    setLoading(true)
    setError(null)
    host.replaceChildren()

    void (async () => {
      try {
        const blob = await fetchDocumentBlob(documentId)
        if (cancelled) return
        await renderAsync(blob, host, undefined, {
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
          className: 'docx-preview-page',
        })
      } catch {
        if (cancelled) return
        try {
          const html = await fetchDocumentHtmlPreview(documentId)
          if (!cancelled) {
            setServerHtml(html)
            setUseServerHtml(true)
          }
        } catch {
          if (!cancelled) setError('Could not render this Word document.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
      host.innerHTML = ''
    }
  }, [documentId, host, useServerHtml])

  if (useServerHtml && serverHtml) {
    return <HtmlIframePreview html={serverHtml} title={`Word preview: ${filename}`} />
  }

  return (
    <div className="relative h-full min-h-[480px] overflow-auto bg-zinc-200/70">
      {loading && (
        <p className="absolute inset-x-0 top-4 z-10 text-center text-sm text-zinc-600">
          Rendering Word document…
        </p>
      )}
      {error && (
        <p className="m-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="docx-preview-root flex justify-center px-4 py-6">
        <div ref={setHost} className="docx-preview-mount" />
      </div>
    </div>
  )
}
