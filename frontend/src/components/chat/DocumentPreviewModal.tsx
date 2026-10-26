import { ExternalLink, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { DocumentHit, DocumentPreview } from '../../api/types'
import { openDocumentInNewTab } from '../../lib/documentFile'
import { splitTextWithHighlight } from '../../lib/highlightPassage'
import { DocumentNativePreview } from '../documents/DocumentNativePreview'
import { DocumentFileIcon } from './DocumentFileIcon'
import { HighlightedPassage } from './HighlightedPassage'

export function DocumentPreviewModal({
  hit,
  onClose,
}: {
  hit: DocumentHit
  onClose: () => void
}) {
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [textLoading, setTextLoading] = useState(true)
  const highlightRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false
    setTextLoading(true)
    api
      .documentPreview(hit.document_id)
      .then((data) => {
        if (!cancelled) setPreview(data)
      })
      .catch(() => {
        if (!cancelled) setPreview(null)
      })
      .finally(() => {
        if (!cancelled) setTextLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [hit.document_id])

  useEffect(() => {
    if (!textLoading && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [textLoading, preview])

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-stone-900/40 p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="doc-preview-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[94vh] w-full max-w-5xl flex-col overflow-hidden rounded-t-2xl border border-stone-200 bg-white shadow-pop sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex shrink-0 items-start gap-3 border-b border-stone-200 px-4 py-3 sm:px-5">
          <DocumentFileIcon fileKind={hit.file_kind} />
          <div className="min-w-0 flex-1">
            <h2 id="doc-preview-title" className="truncate text-sm font-semibold text-stone-900">
              {hit.filename}
            </h2>
            {hit.page_or_section && (
              <p className="mt-0.5 text-xs text-stone-500">{hit.page_or_section}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-stone-900"
            aria-label="Close preview"
          >
            <X className="size-5" strokeWidth={1.75} />
          </button>
        </header>

        <div className="shrink-0 border-b border-stone-100 bg-amber-50/70 px-4 py-2.5 sm:px-5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-amber-900/80">
            Cited passage
          </p>
          <p className="mt-0.5 text-sm leading-6 text-stone-800">
            <HighlightedPassage text={hit.passage} passage={hit.passage} />
          </p>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden sm:min-h-[420px]">
          <DocumentNativePreview
            documentId={hit.document_id}
            fileKind={hit.file_kind}
            filename={hit.filename}
          />
        </div>

        {preview && preview.segments.length > 0 && (
          <div className="max-h-36 shrink-0 overflow-y-auto border-t border-stone-200 bg-stone-50 px-4 py-3 sm:px-5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-stone-500">
              Citation in extracted text
            </p>
            <div className="mt-2 space-y-3">
              {preview.segments.map((segment, index) => {
                const hasHighlight = splitTextWithHighlight(segment.text, hit.passage).some(
                  (p) => p.highlight,
                )
                if (!hasHighlight) return null
                return (
                  <p
                    key={index}
                    ref={highlightRef}
                    className="text-xs leading-6 text-stone-700"
                  >
                    <HighlightedPassage text={segment.text} passage={hit.passage} />
                  </p>
                )
              })}
            </div>
          </div>
        )}

        <footer className="flex shrink-0 justify-end gap-2 border-t border-stone-200 px-4 py-3 sm:px-5">
          <button
            type="button"
            onClick={() => void openDocumentInNewTab(hit.document_id)}
            className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50"
          >
            <ExternalLink className="size-4" strokeWidth={1.75} aria-hidden />
            Open original file
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-stone-900 px-3 py-2 text-sm font-medium text-white hover:bg-stone-800"
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  )
}
