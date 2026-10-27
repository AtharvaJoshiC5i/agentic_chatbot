import { useEffect, useRef, useState } from 'react'
import { fetchDocumentBlob, fetchDocumentHtmlPreview } from '../../lib/documentFile'
import { CitedDocumentTextPreview } from './CitedDocumentTextPreview'
import { DocxCanvasPreview } from './DocxCanvasPreview'
import { HtmlIframePreview } from './HtmlIframePreview'

function normalizeKind(fileKind: string): string {
  return fileKind.toLowerCase().replace(/^\./, '')
}

export function DocumentNativePreview({
  documentId,
  fileKind,
  filename,
  passage,
  page,
}: {
  documentId: number
  fileKind: string
  filename: string
  passage?: string
  page?: number | null
}) {
  const kind = normalizeKind(fileKind)
  const citedPassage = passage?.trim() ?? ''
  const useCitedPdfView = kind === 'pdf' && citedPassage.length > 0

  const blobUrlRef = useRef<string | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [htmlPreview, setHtmlPreview] = useState<string | null>(null)
  const [plainText, setPlainText] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (kind === 'docx' || useCitedPdfView) return

      setLoading(true)
      setError(null)
      setPdfUrl(null)
      setHtmlPreview(null)
      setPlainText(null)

      try {
        if (kind === 'pdf') {
          const blob = await fetchDocumentBlob(documentId)
          const url = URL.createObjectURL(blob)
          blobUrlRef.current = url
          if (!cancelled) setPdfUrl(url)
          return
        }

        if (kind === 'eml' || kind === 'txt' || kind === 'text') {
          const html = await fetchDocumentHtmlPreview(documentId)
          if (!cancelled) setHtmlPreview(html)
          return
        }

        const blob = await fetchDocumentBlob(documentId)
        const text = await blob.text()
        if (!cancelled) setPlainText(text || 'No preview available for this file type.')
      } catch {
        if (!cancelled) {
          setError('Could not render a live preview for this file.')
        }
      } finally {
        if (!cancelled && kind !== 'docx') setLoading(false)
      }
    }

    void load()

    return () => {
      cancelled = true
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [documentId, kind, useCitedPdfView])

  if (useCitedPdfView) {
    return (
      <CitedDocumentTextPreview
        documentId={documentId}
        filename={filename}
        passage={citedPassage}
        page={page}
      />
    )
  }

  if (kind === 'docx') {
    return <DocxCanvasPreview documentId={documentId} filename={filename} passage={passage} />
  }

  if (loading) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center">
        <p className="text-sm text-zinc-500">Rendering preview…</p>
      </div>
    )
  }

  if (error) {
    return (
      <p className="m-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {error}
      </p>
    )
  }

  if (pdfUrl) {
    return (
      <div className="flex h-full min-h-[480px] flex-col bg-zinc-100">
        <iframe
          title={`PDF preview: ${filename}`}
          src={page ? `${pdfUrl}#page=${page}` : pdfUrl}
          className="min-h-[480px] w-full flex-1 border-0 bg-white"
        />
      </div>
    )
  }

  if (htmlPreview) {
    return <HtmlIframePreview html={htmlPreview} title={`Document preview: ${filename}`} passage={passage} />
  }

  if (plainText != null) {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto bg-white px-5 py-4">
        <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-zinc-800">{plainText}</pre>
      </div>
    )
  }

  return null
}
