import { ChevronLeft, ChevronRight, Table2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { StructuredTableRowsResponse, StructuredTableSummary } from '../../api/types'
import type { StructuredDeepLink } from '../../lib/dataExplorerNav'

const PAGE_SIZE = 50

function RecordDrawer({
  row,
  columns,
  onClose,
}: {
  row: Record<string, string>
  columns: string[]
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-stone-900/20"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-lg flex-col border-l border-stone-200 bg-white shadow-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-stone-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-stone-900">Record detail</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-xs font-medium text-stone-600 hover:bg-stone-100"
          >
            Close
          </button>
        </header>
        <dl className="min-h-0 flex-1 overflow-y-auto divide-y divide-stone-100">
          {columns.map((col) => (
            <div key={col} className="px-4 py-3">
              <dt className="font-mono text-[11px] font-medium uppercase tracking-wide text-stone-500">
                {col}
              </dt>
              <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-stone-900">
                {row[col] || '—'}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}

function rowIsFocused(row: Record<string, string>, focus: StructuredDeepLink | null): boolean {
  if (!focus?.column) return false
  return row[focus.column] === focus.value
}

export function StructuredDataPanel({ focus = null }: { focus?: StructuredDeepLink | null }) {
  const [tables, setTables] = useState<StructuredTableSummary[]>([])
  const [activeTable, setActiveTable] = useState<string | null>(null)
  const [rowsPayload, setRowsPayload] = useState<StructuredTableRowsResponse | null>(null)
  const [offset, setOffset] = useState(0)
  const [loadingTables, setLoadingTables] = useState(true)
  const [loadingRows, setLoadingRows] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRow, setSelectedRow] = useState<Record<string, string> | null>(null)
  const [activeFocus, setActiveFocus] = useState<StructuredDeepLink | null>(null)

  useEffect(() => {
    if (focus?.table) {
      setActiveTable(focus.table)
      setOffset(0)
    }
  }, [focus?.table, focus?.column, focus?.value])

  useEffect(() => {
    setLoadingTables(true)
    api
      .dataBrowserTables()
      .then((res) => {
        setTables(res.tables)
        if (res.tables.length) {
          setActiveTable((prev) => {
            if (prev) return prev
            if (focus?.table && res.tables.some((t) => t.name === focus.table)) return focus.table
            return res.tables[0].name
          })
        }
      })
      .catch(() => setError('Could not load tables.'))
      .finally(() => setLoadingTables(false))
  }, [focus?.table])

  const loadRows = useCallback(
    (table: string, pageOffset: number, match?: { col: string; val: string }) => {
      setLoadingRows(true)
      setError(null)
      api
        .dataBrowserTableRows(table, {
          limit: PAGE_SIZE,
          offset: pageOffset,
          col: match?.col,
          val: match?.val,
        })
        .then((payload) => {
          setRowsPayload(payload)
          if (payload.matched && payload.rows[0]) {
            setSelectedRow(payload.rows[0])
            setActiveFocus({
              table: payload.table_name,
              column: payload.matched.column,
              value: payload.matched.value,
            })
          }
        })
        .catch(() => setError('Could not load table rows.'))
        .finally(() => setLoadingRows(false))
    },
    [],
  )

  useEffect(() => {
    if (!activeTable) return
    const deep =
      focus?.table === activeTable && focus.column && focus.value && offset === 0
        ? { col: focus.column, val: focus.value }
        : undefined
    if (!deep) setActiveFocus(null)
    loadRows(activeTable, offset, deep)
  }, [activeTable, offset, loadRows, focus?.table, focus?.column, focus?.value])

  function selectTable(name: string) {
    setActiveTable(name)
    setOffset(0)
    setSelectedRow(null)
    setActiveFocus(null)
  }

  const highlight = activeFocus?.table === activeTable ? activeFocus : null

  const total = rowsPayload?.total ?? 0
  const pageStart = total === 0 ? 0 : offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <aside className="chat-sidebar flex w-full shrink-0 flex-col border-b border-stone-200/90 lg:w-56 lg:border-b-0 lg:border-r">
        <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
          Tables
        </p>
        <nav className="max-h-48 overflow-y-auto lg:max-h-none lg:flex-1 lg:overflow-y-auto">
          {loadingTables && <p className="px-3 py-2 text-xs text-stone-500">Loading…</p>}
          <ul className="space-y-0.5 px-2 pb-3">
            {tables.map((t) => {
              const active = t.name === activeTable
              return (
                <li key={t.name}>
                  <button
                    type="button"
                    onClick={() => selectTable(t.name)}
                    className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors ${
                      active
                        ? 'bg-stone-100 font-medium text-stone-900'
                        : 'text-stone-600 hover:bg-stone-200/50'
                    }`}
                  >
                    <Table2 className="size-3.5 shrink-0 text-stone-400" strokeWidth={1.75} />
                    <span className="min-w-0 flex-1 truncate">{t.label}</span>
                    <span className="tabular-nums text-[11px] text-stone-400">{t.row_count}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 bg-white px-4 py-2.5">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">
              {rowsPayload?.label ?? 'Select a table'}
            </h2>
            {rowsPayload && (
              <p className="text-[11px] text-stone-500">
                {rowsPayload.total.toLocaleString()} rows · {rowsPayload.columns.length} columns
              </p>
            )}
          </div>
          {total > 0 && (
            <div className="flex items-center gap-2 text-xs text-stone-600">
              <span className="tabular-nums">
                {pageStart}–{pageEnd} of {total.toLocaleString()}
              </span>
              <button
                type="button"
                disabled={offset <= 0 || loadingRows}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                className="inline-flex size-8 items-center justify-center rounded-md border border-stone-200 disabled:opacity-40"
                aria-label="Previous page"
              >
                <ChevronLeft className="size-4" />
              </button>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= total || loadingRows}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                className="inline-flex size-8 items-center justify-center rounded-md border border-stone-200 disabled:opacity-40"
                aria-label="Next page"
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
          )}
        </header>

        <div className="min-h-0 flex-1 overflow-auto">
          {error && (
            <p className="m-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
          {loadingRows && !rowsPayload && (
            <p className="p-4 text-sm text-stone-500">Loading rows…</p>
          )}
          {rowsPayload && rowsPayload.columns.length > 0 && (
            <table className="min-w-full text-left text-xs">
              <thead className="sticky top-0 z-10 bg-stone-50 text-[11px] font-semibold uppercase tracking-wide text-stone-500 shadow-[0_1px_0_0_var(--color-line)]">
                <tr>
                  {rowsPayload.columns.map((col) => (
                    <th key={col} className="px-3 py-2 whitespace-nowrap">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 bg-white">
                {rowsPayload.rows.map((row, ri) => (
                  <tr
                    key={ri}
                    className={`cursor-pointer text-stone-800 hover:bg-stone-50 ${
                      rowIsFocused(row, highlight) ? 'bg-amber-50/90 ring-1 ring-inset ring-amber-300/80' : ''
                    }`}
                    onClick={() => setSelectedRow(row)}
                  >
                    {rowsPayload.columns.map((col) => (
                      <td key={col} className="max-w-[14rem] truncate px-3 py-2 align-top">
                        {row[col] || '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {rowsPayload && rowsPayload.rows.length === 0 && !loadingRows && (
            <p className="p-8 text-center text-sm text-stone-500">This table is empty.</p>
          )}
        </div>
      </div>

      {selectedRow && rowsPayload && (
        <RecordDrawer
          row={selectedRow}
          columns={rowsPayload.columns}
          onClose={() => setSelectedRow(null)}
        />
      )}
    </div>
  )
}
