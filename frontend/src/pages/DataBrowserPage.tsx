import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DataBrowserOverview } from '../api/types'
import { DocumentsPanel } from '../components/data-browser/DocumentsPanel'
import { StructuredDataPanel } from '../components/data-browser/StructuredDataPanel'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { panelTitle, segmentedTab } from '../components/ui/styles'

type Tab = 'structured' | 'documents'

export function DataBrowserPage() {
  const [tab, setTab] = useState<Tab>('structured')
  const [overview, setOverview] = useState<DataBrowserOverview | null>(null)

  useEffect(() => {
    api.dataBrowserOverview().then(setOverview).catch(() => setOverview(null))
  }, [])

  return (
    <div className="workspace-shell flex h-dvh flex-col overflow-hidden font-sans text-stone-900">
      <WorkspaceNav />
      <div className="shrink-0 border-b border-stone-200 bg-white px-4 py-6 sm:px-6">
        <p className={panelTitle}>Operations data</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">Data explorer</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-stone-600">
          Browse structured SQLite tables and unstructured documents indexed for the returns agent.
        </p>
        {overview && !overview.database_file_exists && overview.structured_row_count === 0 && (
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="alert">
            No data loaded yet. From the repo root run{' '}
            <code className="rounded bg-amber-100/80 px-1">python scripts/load_database.py</code>, then refresh
            this page.
          </p>
        )}
        {overview?.database_file && (
          <p className="mt-3 text-xs text-stone-500">
            SQLite file:{' '}
            <code className="break-all rounded bg-stone-100 px-1 py-0.5 text-stone-700">
              {overview.database_file}
            </code>
            {overview.database_file_exists ? '' : ' (file not found — run load_database.py)'}
          </p>
        )}
        {overview && (
          <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-stone-600">
            <div>
              <span className="font-semibold tabular-nums text-stone-900">
                {overview.structured_table_count}
              </span>{' '}
              tables
            </div>
            <div>
              <span className="font-semibold tabular-nums text-stone-900">
                {overview.structured_row_count.toLocaleString()}
              </span>{' '}
              structured rows
            </div>
            <div>
              <span className="font-semibold tabular-nums text-stone-900">
                {overview.document_count.toLocaleString()}
              </span>{' '}
              documents
            </div>
          </dl>
        )}
        <div className="ui-segmented mt-4" role="tablist" aria-label="Data type">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'structured'}
            onClick={() => setTab('structured')}
            className={segmentedTab(tab === 'structured')}
          >
            Structured
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'documents'}
            onClick={() => setTab('documents')}
            className={segmentedTab(tab === 'documents')}
          >
            Documents
          </button>
        </div>
      </div>

      <main className="workspace-main min-h-0 flex-1 overflow-hidden">
        {tab === 'structured' ? <StructuredDataPanel /> : <DocumentsPanel />}
      </main>
    </div>
  )
}
