import { useState } from 'react'
import type { DocumentHit } from '../../api/types'
import { DocumentFileIcon } from './DocumentFileIcon'
import { DocumentPreviewModal } from './DocumentPreviewModal'

function excerpt(passage: string, max = 140): string {
  const t = passage.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

export function DocumentSources({ sources }: { sources: DocumentHit[] }) {
  const [previewHit, setPreviewHit] = useState<DocumentHit | null>(null)

  if (!sources.length) return null

  return (
    <>
      <section
        className="mt-5 overflow-hidden rounded-md border border-stone-200 bg-white"
        aria-labelledby="document-sources-title"
      >
        <div className="border-b border-stone-100 bg-stone-50/80 px-4 py-2.5">
          <h3 id="document-sources-title" className="text-xs font-semibold uppercase tracking-wide text-stone-600">
            Documents
          </h3>
        </div>
        <ul className="divide-y divide-stone-100">
          {sources.map((hit, index) => (
            <li key={`${hit.document_id}-${index}`}>
              <button
                type="button"
                onClick={() => setPreviewHit(hit)}
                className="flex w-full gap-3 px-4 py-3.5 text-left transition-colors hover:bg-stone-50/80 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-600"
              >
                <DocumentFileIcon fileKind={hit.file_kind} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-stone-900">
                    {hit.filename}
                  </span>
                  {hit.page_or_section && (
                    <span className="mt-0.5 block text-xs text-stone-500">{hit.page_or_section}</span>
                  )}
                  <span className="mt-2 block text-[13px] leading-5 text-stone-600">
                    {excerpt(hit.passage)}
                  </span>
                  {hit.relevance_score != null && (
                    <span className="mt-1.5 inline-block text-[11px] text-stone-400 tabular-nums">
                      Relevance {Math.round(hit.relevance_score * 100)}%
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {previewHit && (
        <DocumentPreviewModal hit={previewHit} onClose={() => setPreviewHit(null)} />
      )}
    </>
  )
}
