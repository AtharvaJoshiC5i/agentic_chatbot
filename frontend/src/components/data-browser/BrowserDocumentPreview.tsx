import { ChevronDown, ExternalLink, FileText } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { DocumentBrowserItem, DocumentPreview } from '../../api/types'
import { openDocumentInNewTab } from '../../lib/documentFile'
import { DocumentFileIcon } from '../chat/DocumentFileIcon'
import { HighlightedPassage } from '../chat/HighlightedPassage'
import { DocumentNativePreview } from '../documents/DocumentNativePreview'

export function BrowserDocumentPreview({
  doc,
  highlightPassage,
  highlightPage,
}: {
  doc: DocumentBrowserItem | null
  highlightPassage?: string
  highlightPage?: number
}) {
  const highlightRef = useRef<HTMLDivElement | null>(null)
  const [extracted, setExtracted] = useState<DocumentPreview | null>(null)
  const [showExtracted, setShowExtracted] = useState(Boolean(highlightPassage?.trim()))

  const docId = doc?.document_id

  useEffect(() => {
    if (docId === undefined) {
      setExtracted(null)
      return
    }
    let cancelled = false
    api
      .documentPreview(docId)
      .then((data) => {
        if (!cancelled) setExtracted(data)
      })
      .catch(() => {
        if (!cancelled) setExtracted(null)
      })
    return () => {
      cancelled = true
    }
  }, [docId])

  useEffect(() => {
    if (highlightPassage?.trim()) setShowExtracted(true)
  }, [highlightPassage, docId])

  useEffect(() => {
    if (!showExtracted || !highlightPassage?.trim()) return
    const el = highlightRef.current
    if (!el) return
    const t = window.setTimeout(() => {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 120)
    return () => window.clearTimeout(t)
  }, [showExtracted, highlightPassage, extracted])

  if (!doc) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <FileText className="size-10 text-zinc-300" strokeWidth={1.25} aria-hidden />
        <p className="text-sm text-zinc-500">Select a document to open a live PDF, Word, or email preview.</p>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="shrink-0 border-b border-zinc-200 bg-white px-4 py-3 sm:px-5">
        <div className="flex items-start gap-3">
          <DocumentFileIcon fileKind={doc.file_kind} />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-zinc-900">{doc.filename}</h2>
            <p className="mt-0.5 font-mono text-[11px] text-zinc-500">{doc.file_path}</p>
            <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-600">
              <div>
                <span className="text-zinc-400">Type </span>
                {doc.document_type}
              </div>
              {doc.return_id && (
                <div>
                  <span className="text-zinc-400">Return </span>
                  <span className="font-mono">{doc.return_id}</span>
                </div>
              )}
              {doc.product_id && (
                <div>
                  <span className="text-zinc-400">Product </span>
                  <span className="font-mono">{doc.product_id}</span>
                </div>
              )}
            </dl>
          </div>
          <button
            type="button"
            onClick={() => void openDocumentInNewTab(doc.document_id)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
          >
            <ExternalLink className="size-3.5" strokeWidth={1.75} aria-hidden />
            Original
          </button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-hidden border-b border-zinc-200">
        <DocumentNativePreview
          documentId={doc.document_id}
          fileKind={doc.file_kind}
          filename={doc.filename}
          passage={highlightPassage}
          page={highlightPage}
        />
      </div>

      {extracted && (
        <div className="shrink-0 bg-zinc-50">
          <button
            type="button"
            onClick={() => setShowExtracted((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-left text-xs font-medium text-zinc-600 hover:bg-zinc-100/80"
          >
            Extracted text (used by search)
            <ChevronDown
              className={`size-4 transition-transform ${showExtracted ? 'rotate-180' : ''}`}
              strokeWidth={1.75}
            />
          </button>
          {showExtracted && (
            <div
              ref={highlightRef}
              className="max-h-48 overflow-y-auto border-t border-zinc-200 bg-white px-4 py-3"
            >
              <pre className="whitespace-pre-wrap font-sans text-xs leading-6 text-zinc-700">
                {highlightPassage?.trim() ? (
                  <HighlightedPassage text={extracted.full_text} passage={highlightPassage} />
                ) : (
                  extracted.full_text
                )}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
