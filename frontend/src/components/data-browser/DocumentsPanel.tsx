import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { DocumentBrowserItem } from '../../api/types'
import { humanize } from '../../lib/format'
import { DocumentFileIcon } from '../chat/DocumentFileIcon'
import { BrowserDocumentPreview } from './BrowserDocumentPreview'

const PAGE_SIZE = 40

export function DocumentsPanel() {
  const [items, setItems] = useState<DocumentBrowserItem[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [documentTypes, setDocumentTypes] = useState<string[]>([])
  const [typeFilter, setTypeFilter] = useState('')
  const [returnFilter, setReturnFilter] = useState('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selected, setSelected] = useState<DocumentBrowserItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 250)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => {
    setOffset(0)
  }, [typeFilter, returnFilter, debouncedSearch])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .dataBrowserDocuments({
        limit: PAGE_SIZE,
        offset,
        document_type: typeFilter || undefined,
        return_id: returnFilter || undefined,
        search: debouncedSearch || undefined,
      })
      .then((res) => {
        setItems(res.items)
        setTotal(res.total)
        setDocumentTypes(res.document_types)
        setSelected((prev) => {
          if (prev && res.items.some((i) => i.document_id === prev.document_id)) return prev
          return res.items[0] ?? null
        })
      })
      .catch(() => setError('Could not load documents.'))
      .finally(() => setLoading(false))
  }, [offset, typeFilter, returnFilter, debouncedSearch])

  const pageStart = total === 0 ? 0 : offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  return (
    <div className="flex h-full min-h-0 flex-col xl:flex-row">
      <div className="flex w-full shrink-0 flex-col border-b border-stone-200 xl:w-[22rem] xl:border-b-0 xl:border-r">
        <div className="space-y-2 border-b border-stone-200 p-3">
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-stone-400"
              strokeWidth={2}
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search filenames"
              className="h-9 w-full rounded-md border border-stone-200 bg-white pr-3 pl-9 text-sm focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/12"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-9 min-w-0 flex-1 rounded-md border border-stone-200 bg-white px-2 text-xs"
              aria-label="Document type"
            >
              <option value="">All types</option>
              {documentTypes.map((t) => (
                <option key={t} value={t}>{humanize(t)}</option>
              ))}
            </select>
            <input
              type="text"
              value={returnFilter}
              onChange={(e) => setReturnFilter(e.target.value)}
              placeholder="Return ID"
              className="h-9 w-24 rounded-md border border-stone-200 bg-white px-2 font-mono text-xs uppercase"
            />
          </div>
          {total > 0 && (
            <div className="flex items-center justify-between text-[11px] text-stone-500">
              <span className="tabular-nums">
                {pageStart}–{pageEnd} of {total.toLocaleString()}
              </span>
              <div className="flex gap-1">
                <button
                  type="button"
                  disabled={offset <= 0}
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                  className="inline-flex size-7 items-center justify-center rounded border border-stone-200 disabled:opacity-40"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="size-3.5" />
                </button>
                <button
                  type="button"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                  className="inline-flex size-7 items-center justify-center rounded border border-stone-200 disabled:opacity-40"
                  aria-label="Next page"
                >
                  <ChevronRight className="size-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        <ul className="min-h-0 flex-1 overflow-y-auto divide-y divide-stone-100">
          {loading && items.length === 0 && (
            <li className="p-4 text-sm text-stone-500">Loading documents…</li>
          )}
          {error && (
            <li className="m-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </li>
          )}
          {!loading && items.length === 0 && !error && (
            <li className="p-6 text-center text-sm text-stone-500">
              No documents match your filters. Ingest unstructured data into{' '}
              <code className="text-xs">document_metadata</code>.
            </li>
          )}
          {items.map((doc) => {
            const active = selected?.document_id === doc.document_id
            return (
              <li key={doc.document_id}>
                <button
                  type="button"
                  onClick={() => setSelected(doc)}
                  className={`flex w-full gap-2 px-3 py-2.5 text-left transition-colors ${
                    active
                      ? 'bg-stone-100'
                      : 'hover:bg-stone-50/90'
                  }`}
                >
                  <DocumentFileIcon fileKind={doc.file_kind} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-stone-900">
                      {doc.filename}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-stone-500">
                      {humanize(doc.document_type)}
                      {doc.return_id ? ` · ${doc.return_id}` : ''}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="min-h-[50vh] min-w-0 flex-1 xl:min-h-0">
        <BrowserDocumentPreview doc={selected} />
      </div>
    </div>
  )
}
