import { FileText } from 'lucide-react'
import { useState } from 'react'
import type { DocumentHit, StructuredEvidence, SupportingEvidence } from '../../api/types'
import { DocumentPreviewModal } from './DocumentPreviewModal'
import { RecordEvidenceModal } from './RecordEvidenceModal'

export function SourceChips({ bundle }: { bundle: SupportingEvidence | null | undefined }) {
  const [docPreview, setDocPreview] = useState<DocumentHit | null>(null)
  const [record, setRecord] = useState<StructuredEvidence | null>(null)

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
              onClick={() => setDocPreview(d)}
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 transition-colors hover:border-stone-300 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
            >
              <FileText className="size-3.5 shrink-0 text-stone-500" aria-hidden />
              <span className="truncate">{d.filename}</span>
            </button>
          ))}
          {structured.map((s) => (
            <button
              key={`${s.table_name}-${s.title}`}
              type="button"
              onClick={() => setRecord(s)}
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 transition-colors hover:border-stone-300 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
            >
              <span className="truncate">{s.title}</span>
            </button>
          ))}
        </div>
      </div>
      {docPreview && (
        <DocumentPreviewModal hit={docPreview} onClose={() => setDocPreview(null)} />
      )}
      {record && <RecordEvidenceModal item={record} onClose={() => setRecord(null)} />}
    </>
  )
}
