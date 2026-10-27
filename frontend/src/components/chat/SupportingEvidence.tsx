import { ChevronDown, Database, FileStack, Table2 } from 'lucide-react'
import { useId, useState } from 'react'
import type { DocumentHit, StructuredEvidence, SupportingEvidence as EvidenceBundle } from '../../api/types'
import { humanize } from '../../lib/format'
import { DocumentFileIcon } from './DocumentFileIcon'
import { SourcePreviewModal, type SourcePreviewState } from './SourcePreviewModal'

function excerpt(passage: string, max = 140): string {
  const t = passage.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

function formatPreviewValue(raw: string): string {
  const t = raw.trim()
  if (!t) return '—'
  if (t.length > 56) return `${t.slice(0, 55)}…`
  return t
}

function previewFields(item: StructuredEvidence, limit = 3): { key: string; value: string }[] {
  const row = item.rows[0]
  if (!row) return []
  const cols = item.columns.length ? item.columns : Object.keys(row)
  return cols.slice(0, limit).map((key) => ({
    key,
    value: formatPreviewValue(String(row[key] ?? '')),
  }))
}

function StructuredEvidenceRow({
  item,
  onOpen,
}: {
  item: StructuredEvidence
  onOpen: () => void
}) {
  const fields = previewFields(item)

  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="group flex w-full items-start gap-2.5 rounded-md border border-stone-200 bg-white p-3 text-left transition-colors hover:border-stone-300 hover:bg-stone-50/80"
      >
        <span
          className="flex size-8 shrink-0 items-center justify-center rounded-md bg-stone-100 text-stone-600"
          aria-hidden
        >
          <Database className="size-4" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-stone-900">{item.title}</p>
          <p className="mt-0.5 font-mono text-[10px] text-stone-500">{item.table_name}</p>
          {fields.length > 0 && (
            <dl className="mt-2 space-y-1 text-[11px]">
              {fields.map(({ key, value }) => (
                <div key={key} className="grid grid-cols-[minmax(0,38%)_1fr] gap-2">
                  <dt className="truncate text-stone-500">{humanize(key)}</dt>
                  <dd className="truncate text-stone-800">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </button>
    </li>
  )
}

function DocumentEvidenceRow({
  hit,
  onOpen,
}: {
  hit: DocumentHit
  onOpen: () => void
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="group flex w-full gap-2.5 rounded-md border border-stone-200 bg-white p-3 text-left transition-colors hover:border-stone-300 hover:bg-stone-50/80"
      >
        <DocumentFileIcon fileKind={hit.file_kind} />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-stone-900">{hit.filename}</p>
          {hit.page_or_section && (
            <p className="mt-0.5 text-[10px] font-medium text-stone-500">{hit.page_or_section}</p>
          )}
          <p className="mt-1.5 text-[12px] leading-relaxed text-stone-600">{excerpt(hit.passage)}</p>
        </div>
      </button>
    </li>
  )
}

export function SupportingEvidence({ bundle }: { bundle: EvidenceBundle | null | undefined }) {
  const [open, setOpen] = useState(false)
  const [preview, setPreview] = useState<SourcePreviewState>(null)
  const panelId = useId()
  const titleId = useId()

  if (!bundle) return null
  const { structured, documents } = bundle
  if (!structured.length && !documents.length) return null

  const total = structured.length + documents.length

  return (
    <>
      <section className="mt-5 border-t border-stone-200/90 pt-3" aria-labelledby={titleId}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex w-full items-center gap-2 rounded-lg py-1.5 text-left transition-colors hover:bg-stone-50/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
        >
          <ChevronDown
            className={`size-4 shrink-0 text-stone-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
            strokeWidth={1.75}
            aria-hidden
          />
          <span id={titleId} className="text-[13px] font-semibold text-stone-900">
            Sources ({total})
          </span>
        </button>

        <div id={panelId} hidden={!open} className="mt-2 space-y-4 border-t border-stone-100 pt-3">
          {structured.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-1.5 px-0.5">
                <Table2 className="size-3.5 text-stone-400" strokeWidth={1.75} aria-hidden />
                <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-stone-500">
                  Records
                </h4>
              </div>
              <ul className="space-y-2">
                {structured.map((item) => (
                  <StructuredEvidenceRow
                    key={item.evidence_id}
                    item={item}
                    onOpen={() => setPreview({ kind: 'structured', item })}
                  />
                ))}
              </ul>
            </div>
          )}

          {documents.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-1.5 px-0.5">
                <FileStack className="size-3.5 text-stone-400" strokeWidth={1.75} aria-hidden />
                <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-stone-500">
                  Documents
                </h4>
              </div>
              <ul className="space-y-2">
                {documents.map((hit, index) => (
                  <DocumentEvidenceRow
                    key={`${hit.document_id}-${index}`}
                    hit={hit}
                    onOpen={() => setPreview({ kind: 'document', hit })}
                  />
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>
      <SourcePreviewModal state={preview} onClose={() => setPreview(null)} />
    </>
  )
}
