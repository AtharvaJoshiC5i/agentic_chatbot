import { ChevronDown, ChevronRight, Database, FileStack, Table2 } from 'lucide-react'
import { useId, useState } from 'react'
import type { DocumentHit, StructuredEvidence, SupportingEvidence as EvidenceBundle } from '../../api/types'
import { humanize } from '../../lib/format'
import { DocumentFileIcon } from './DocumentFileIcon'
import { DocumentPreviewModal } from './DocumentPreviewModal'
import { RecordEvidenceModal } from './RecordEvidenceModal'

function excerpt(passage: string, max = 140): string {
  const t = passage.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

function formatPreviewValue(raw: string): string {
  const t = raw.trim()
  if (!t) return '—'
  if (t.startsWith('[') || t.startsWith('{')) {
    try {
      const parsed = JSON.parse(t) as unknown
      if (Array.isArray(parsed)) {
        if (parsed.length === 0) return 'None'
        return `${parsed.length} item${parsed.length === 1 ? '' : 's'}`
      }
      if (parsed && typeof parsed === 'object') return 'Object'
    } catch {
      /* keep string */
    }
  }
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

function StructuredEvidenceCard({ item }: { item: StructuredEvidence }) {
  const [open, setOpen] = useState(false)
  const fields = previewFields(item)
  const rowLabel =
    item.rows.length === 1
      ? '1 row'
      : item.rows.length > 1
        ? `${item.rows.length} rows`
        : null

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group flex h-full w-full flex-col rounded-md border border-stone-200 bg-white p-3 text-left transition-colors hover:border-stone-300 hover:bg-stone-50/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
      >
        <div className="flex items-start gap-2.5">
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-stone-100 text-stone-600"
            aria-hidden
          >
            <Database className="size-4" strokeWidth={1.75} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex items-start justify-between gap-2">
              <span className="line-clamp-2 text-[13px] font-semibold leading-snug text-stone-900">
                {item.title}
              </span>
              <ChevronRight
                className="size-4 shrink-0 text-stone-400 transition-colors group-hover:text-accent-700"
                strokeWidth={1.75}
                aria-hidden
              />
            </span>
            <span className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="rounded-md bg-stone-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-stone-600 ring-1 ring-stone-200/80">
                {item.table_name}
              </span>
              {rowLabel && (
                <span className="text-[10px] font-medium text-stone-400">{rowLabel}</span>
              )}
            </span>
          </span>
        </div>

        {fields.length > 0 && (
          <dl className="mt-3 space-y-1.5 border-t border-stone-100 pt-2.5">
            {fields.map(({ key, value }) => (
              <div key={key} className="grid grid-cols-[minmax(0,38%)_1fr] gap-2 text-[11px] leading-snug">
                <dt className="truncate font-medium text-stone-500">{humanize(key)}</dt>
                <dd className="truncate text-stone-800" title={value}>{value}</dd>
              </div>
            ))}
          </dl>
        )}

        <span className="mt-2.5 text-[11px] font-medium text-accent-800/90 group-hover:text-accent-700">
          Open full record
        </span>
      </button>
      {open && <RecordEvidenceModal item={item} onClose={() => setOpen(false)} />}
    </>
  )
}

function DocumentEvidenceCard({
  hit,
  onOpen,
}: {
  hit: DocumentHit
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex w-full gap-2.5 rounded-md border border-stone-200 bg-white p-3 text-left transition-colors hover:border-stone-300 hover:bg-stone-50/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
    >
      <DocumentFileIcon fileKind={hit.file_kind} />
      <span className="min-w-0 flex-1">
        <span className="flex items-start justify-between gap-2">
          <span className="line-clamp-1 text-[13px] font-semibold text-stone-900">{hit.filename}</span>
          <ChevronRight
            className="size-4 shrink-0 text-stone-400 group-hover:text-accent-700"
            strokeWidth={1.75}
            aria-hidden
          />
        </span>
        {hit.page_or_section && (
          <span className="mt-0.5 block text-[10px] font-medium text-stone-500">{hit.page_or_section}</span>
        )}
        <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-stone-600">
          {excerpt(hit.passage)}
        </p>
      </span>
    </button>
  )
}

export function SupportingEvidence({ bundle }: { bundle: EvidenceBundle | null | undefined }) {
  const [previewHit, setPreviewHit] = useState<DocumentHit | null>(null)
  const [open, setOpen] = useState(false)
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
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span id={titleId} className="text-[13px] font-semibold text-stone-900">
                Supporting evidence
              </span>
              <span
                className="rounded-md bg-stone-100 px-2 py-0.5 text-[10px] font-medium tabular-nums text-stone-600"
              >
                {total} source{total === 1 ? '' : 's'}
              </span>
            </span>
            <span className="mt-0.5 block text-[11px] text-stone-500">
              {open ? 'Hide sources' : 'Show sources used for this answer'}
            </span>
          </span>
        </button>

        <div
          id={panelId}
          hidden={!open}
          className="mt-2 space-y-4 border-t border-stone-100 pt-3"
        >
          {structured.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-1.5 px-0.5">
                <Table2 className="size-3.5 text-stone-400" strokeWidth={1.75} aria-hidden />
                <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-stone-500">
                  Structured data
                </h4>
                <span className="text-[10px] tabular-nums text-stone-400">{structured.length}</span>
              </div>
              <ul className="grid gap-2.5 sm:grid-cols-2">
                {structured.map((item) => (
                  <li key={item.evidence_id} className="min-h-0">
                    <StructuredEvidenceCard item={item} />
                  </li>
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
                <span className="text-[10px] tabular-nums text-stone-400">{documents.length}</span>
              </div>
              <ul className="grid gap-2.5 sm:grid-cols-2">
                {documents.map((hit, index) => (
                  <li key={`${hit.document_id}-${index}`}>
                    <DocumentEvidenceCard hit={hit} onOpen={() => setPreviewHit(hit)} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      {previewHit && (
        <DocumentPreviewModal hit={previewHit} onClose={() => setPreviewHit(null)} />
      )}
    </>
  )
}
