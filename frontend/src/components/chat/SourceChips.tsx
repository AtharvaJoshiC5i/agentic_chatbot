import { Database, FileText } from 'lucide-react'
import { useState } from 'react'
import type { SupportingEvidence } from '../../api/types'
import { SourcePreviewModal, type SourcePreviewState } from './SourcePreviewModal'

const chipClass =
  'inline-flex max-w-full items-center gap-1.5 rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs font-medium text-stone-700 transition-colors hover:border-stone-300 hover:bg-stone-100'

export function SourceChips({ bundle }: { bundle: SupportingEvidence | null | undefined }) {
  const [preview, setPreview] = useState<SourcePreviewState>(null)
  if (!bundle) return null
  const { structured, documents } = bundle
  const total = structured.length + documents.length
  if (!total) return null

  return (
    <>
      <div className="mt-4">
        <p className="mb-2 text-xs font-medium text-stone-600">Sources ({total})</p>
        <div className="flex flex-wrap gap-2">
          {documents.map((d) => (
            <button
              key={d.document_id}
              type="button"
              className={chipClass}
              onClick={() => setPreview({ kind: 'document', hit: d })}
            >
              <FileText className="size-3.5 shrink-0 text-stone-500" aria-hidden />
              <span className="truncate">{d.filename}</span>
            </button>
          ))}
          {structured.map((s) => (
            <button
              key={s.evidence_id}
              type="button"
              className={chipClass}
              onClick={() => setPreview({ kind: 'structured', item: s })}
            >
              <Database className="size-3.5 shrink-0 text-stone-500" aria-hidden />
              <span className="truncate">{s.title}</span>
            </button>
          ))}
        </div>
      </div>
      <SourcePreviewModal state={preview} onClose={() => setPreview(null)} />
    </>
  )
}
