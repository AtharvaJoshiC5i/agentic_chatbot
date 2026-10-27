import { X } from 'lucide-react'
import { useEffect } from 'react'
import type { DocumentHit, StructuredEvidence } from '../../api/types'
import { DocumentFileIcon } from './DocumentFileIcon'
import { StructuredEvidenceDetail } from './StructuredEvidenceDetail'
import { DocumentNativePreview } from '../documents/DocumentNativePreview'

export type SourcePreviewState =
  | { kind: 'document'; hit: DocumentHit }
  | { kind: 'structured'; item: StructuredEvidence }
  | null

function resolvePage(hit: DocumentHit): number | undefined {
  if (hit.page != null && hit.page > 0) return hit.page
  const section = hit.page_or_section ?? ''
  const match = /page\s*(\d+)/i.exec(section)
  return match ? Number(match[1]) : undefined
}

function DocumentSourceBody({ hit }: { hit: DocumentHit }) {
  const passage = hit.passage?.trim() ?? ''
  const page = resolvePage(hit)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <DocumentNativePreview
        documentId={hit.document_id}
        fileKind={hit.file_kind}
        filename={hit.filename}
        passage={passage}
        page={page}
      />
    </div>
  )
}

export function SourcePreviewModal({
  state,
  onClose,
}: {
  state: SourcePreviewState
  onClose: () => void
}) {
  useEffect(() => {
    if (!state) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [state, onClose])

  if (!state) return null

  const title =
    state.kind === 'document' ? state.hit.filename : state.item.title

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-stone-900/40 p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="source-preview-title"
      onClick={onClose}
    >
      <div
        className="flex h-[min(88vh,820px)] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-stone-200 bg-white shadow-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex shrink-0 items-start gap-3 border-b border-stone-200 px-4 py-3 sm:px-5">
          {state.kind === 'document' && <DocumentFileIcon fileKind={state.hit.file_kind} />}
          <div className="min-w-0 flex-1">
            <h2 id="source-preview-title" className="truncate text-sm font-semibold text-stone-900">
              {title}
            </h2>
            {state.kind === 'document' && state.hit.page_or_section && (
              <p className="mt-0.5 text-[11px] text-stone-500">{state.hit.page_or_section}</p>
            )}
            {state.kind === 'structured' && (
              <p className="mt-0.5 font-mono text-[11px] text-stone-500">{state.item.table_name}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100"
            aria-label="Close preview"
          >
            <X className="size-4" strokeWidth={1.75} />
          </button>
        </header>
        {state.kind === 'document' ? (
          <DocumentSourceBody hit={state.hit} />
        ) : (
          <StructuredEvidenceDetail item={state.item} />
        )}
      </div>
    </div>
  )
}
