import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { parseDataExplorerSearch } from '../lib/dataExplorerNav'
import { api } from '../api/client'
import type { DataBrowserOverview } from '../api/types'
import { useToast } from '../context/ToastContext'
import { DocumentsPanel } from '../components/data-browser/DocumentsPanel'
import { StructuredDataPanel } from '../components/data-browser/StructuredDataPanel'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { panelTitle, segmentedTab } from '../components/ui/styles'

type Tab = 'structured' | 'documents'

export function DataBrowserPage() {
  const { showToast } = useToast()
  const [searchParams] = useSearchParams()
  const explorerFocus = useMemo(
    () => parseDataExplorerSearch(searchParams.toString()),
    [searchParams],
  )
  const [tab, setTab] = useState<Tab>(explorerFocus.tab)
  const [overview, setOverview] = useState<DataBrowserOverview | null>(null)
  const [bootstrapping, setBootstrapping] = useState(false)
  const [docListKey, setDocListKey] = useState(0)

  const refreshOverview = useCallback(() => {
    api.dataBrowserOverview().then(setOverview).catch(() => setOverview(null))
  }, [])

  useEffect(() => {
    refreshOverview()
  }, [refreshOverview])

  useEffect(() => {
    setTab(explorerFocus.tab)
  }, [explorerFocus.tab])

  const runDocumentBootstrap = async () => {
    setBootstrapping(true)
    try {
      const res = await api.dataBrowserDocumentsBootstrap()
      if (res.ok) {
        showToast(
          `Loaded ${res.metadata_count} documents (${res.chroma_chunk_count} search chunks indexed).`,
        )
        refreshOverview()
        setDocListKey((k) => k + 1)
        setTab('documents')
      } else {
        showToast(res.errors[0] ?? 'Document bootstrap failed')
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Document bootstrap failed')
    } finally {
      setBootstrapping(false)
    }
  }

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
        {overview && overview.document_count === 0 && overview.structured_row_count > 0 && (
          <div
            className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            role="status"
          >
            <p className="font-medium">Unstructured documents are not loaded yet</p>
            <p className="mt-1 text-amber-900/90">
              {overview.documents_status_message ||
                'Load the document catalog from data/unstructured and index it for the agent.'}
            </p>
            <button
              type="button"
              disabled={bootstrapping}
              onClick={() => runDocumentBootstrap()}
              className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-800 disabled:opacity-60"
            >
              {bootstrapping ? 'Indexing…' : 'Load & index documents'}
            </button>
            <p className="mt-2 text-xs text-amber-800/80">
              CLI: <code className="rounded bg-amber-100/80 px-1">python scripts/bootstrap_documents.py</code>
            </p>
          </div>
        )}
        {overview && !overview.documents_ready && overview.document_count > 0 && (
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {overview.documents_status_message}{' '}
            <button
              type="button"
              className="font-medium underline"
              disabled={bootstrapping}
              onClick={() => runDocumentBootstrap()}
            >
              Re-index for search
            </button>
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
        {tab === 'structured' ? (
          <StructuredDataPanel focus={explorerFocus.structured ?? null} />
        ) : (
          <DocumentsPanel
            refreshKey={docListKey}
            focus={explorerFocus.document ?? null}
            onRequestBootstrap={runDocumentBootstrap}
            bootstrapping={bootstrapping}
          />
        )}
      </main>
    </div>
  )
}
