import type { DocumentHit } from '../../api/types'
import { DocumentFileIcon } from './DocumentFileIcon'

function excerpt(passage: string, max = 140): string {
  const t = passage.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

export function DocumentSources({ sources }: { sources: DocumentHit[] }) {
  if (!sources.length) return null

  return (
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
          <li key={`${hit.document_id}-${index}`} className="flex gap-3 px-4 py-3.5">
            <DocumentFileIcon fileKind={hit.file_kind} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-stone-900">{hit.filename}</span>
              {hit.page_or_section && (
                <span className="mt-0.5 block text-xs text-stone-500">{hit.page_or_section}</span>
              )}
              <span className="mt-2 block text-[13px] leading-5 text-stone-600">{excerpt(hit.passage)}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
