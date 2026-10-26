import { X } from 'lucide-react'
import type { StructuredEvidence } from '../../api/types'

export function RecordEvidenceModal({
  item,
  onClose,
}: {
  item: StructuredEvidence
  onClose: () => void
}) {
  const columns = item.columns.length ? item.columns : Object.keys(item.rows[0] ?? {})

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-stone-900/30 p-0 backdrop-blur-[1px] sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="record-evidence-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-stone-200 bg-white shadow-pop sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-stone-200 px-4 py-3 sm:px-5">
          <div className="min-w-0">
            <h2 id="record-evidence-title" className="text-sm font-semibold text-stone-900">
              {item.title}
            </h2>
            <p className="mt-0.5 font-mono text-[11px] text-stone-500">
              {item.table_name} · {item.source_tool}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-stone-500 hover:bg-stone-100"
            aria-label="Close"
          >
            <X className="size-4" strokeWidth={1.75} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto p-4 sm:p-5">
          {item.rows.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
                  <tr>
                    {columns.map((col) => (
                      <th key={col} className="px-3 py-2 whitespace-nowrap">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {item.rows.map((row, ri) => (
                    <tr key={ri} className="text-stone-800">
                      {columns.map((col) => (
                        <td key={col} className="max-w-xs px-3 py-2 align-top whitespace-pre-wrap">
                          {row[col] ?? ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-stone-500">No rows in this record.</p>
          )}
        </div>
      </div>
    </div>
  )
}
