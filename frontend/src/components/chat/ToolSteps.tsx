import { ChevronRight, Wrench } from 'lucide-react'
import { useState } from 'react'
import type { ToolEvent } from '../../lib/chats'

const DOCUMENT_TOOLS = new Set([
  'search_return_policy',
  'search_inspection_reports',
  'search_customer_complaints',
  'search_warranty_documents',
  'search_supplier_reports',
  'resolve_applicable_policy',
])

export function ToolSteps({ events }: { events: ToolEvent[] }) {
  const [open, setOpen] = useState(true)
  if (!events.length) return null

  return (
    <div className="mt-4 overflow-hidden rounded-lg border border-stone-200 bg-stone-50/60">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left text-sm font-medium text-stone-700 transition-colors hover:bg-stone-100/70"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <ChevronRight
          className={`size-4 text-stone-400 transition-transform ${open ? 'rotate-90' : ''}`}
          aria-hidden
        />
        <Wrench className="size-3.5 text-stone-500" strokeWidth={2} aria-hidden />
        <span>Tool activity</span>
        <span className="ml-auto text-xs font-normal text-stone-500 tabular-nums">
          {events.length} {events.length === 1 ? 'call' : 'calls'}
        </span>
      </button>

      {open && (
        <ol className="divide-y divide-stone-200 border-t border-stone-200">
          {events.map((ev, i) => (
            <li key={i} className="px-3.5 py-3">
              <p className="flex items-center gap-2 text-[13px] font-medium text-stone-900">
                <span className="font-mono text-[11px] text-stone-400 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="font-mono">{ev.tool ?? 'tool'}</span>
              </p>
              {ev.args && Object.keys(ev.args).length > 0 && (
                <pre className="mt-2 overflow-x-auto rounded-md border border-stone-200 bg-white p-2.5 font-mono text-xs leading-5 text-stone-700">
                  {JSON.stringify(ev.args, null, 2)}
                </pre>
              )}
              {ev.result_preview && !DOCUMENT_TOOLS.has(ev.tool ?? '') && (
                <details className="group mt-2">
                  <summary className="cursor-pointer text-xs font-medium text-stone-500 select-none hover:text-stone-900">
                    Result from system
                  </summary>
                  <pre className="mt-2 max-h-64 overflow-auto rounded-md border border-stone-200 bg-white p-2.5 font-mono text-xs leading-5 whitespace-pre-wrap text-stone-700">
                    {ev.result_preview}
                  </pre>
                </details>
              )}
              {ev.result_preview && DOCUMENT_TOOLS.has(ev.tool ?? '') && (
                <p className="mt-2 text-xs text-stone-500">
                  Document hits are listed in the <span className="font-medium text-stone-700">Documents</span>{' '}
                  section above.
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
