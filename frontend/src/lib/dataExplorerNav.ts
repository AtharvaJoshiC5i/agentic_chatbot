import type { DocumentHit, StructuredEvidence } from '../api/types'

/** Preferred primary-key columns when deep-linking structured evidence rows. */
const TABLE_KEY_COLUMNS: Record<string, string[]> = {
  returns: ['return_id'],
  orders: ['order_id'],
  order_items: ['order_item_id'],
  customers: ['customer_id'],
  products: ['product_id'],
  suppliers: ['supplier_id'],
  deliveries: ['delivery_id'],
  inspections: ['inspection_id'],
  refunds: ['refund_id'],
  investigation_cases: ['case_id'],
  product_units: ['product_unit_id', 'serial_number'],
  return_events: ['event_id'],
  action_requests: ['action_id'],
  recovery_tasks: ['recovery_task_id'],
  document_metadata: ['document_id'],
}

function pickRowKey(
  table: string,
  record?: Record<string, unknown> | null,
  row?: Record<string, string>,
): { column: string; value: string } | null {
  const source: Record<string, unknown> = { ...row, ...record }
  const candidates = TABLE_KEY_COLUMNS[table] ?? []
  const fallback = Object.keys(source).filter((k) => k.endsWith('_id') || k === 'serial_number')
  for (const col of [...candidates, ...fallback]) {
    const raw = source[col]
    if (raw != null && String(raw).trim() !== '') {
      return { column: col, value: String(raw).trim() }
    }
  }
  return null
}

export type StructuredDeepLink = {
  table: string
  column: string
  value: string
}

export type DocumentDeepLink = {
  documentId: number
  passage?: string
  page?: number
}

export function structuredEvidencePath(item: StructuredEvidence): string {
  const key = pickRowKey(item.table_name, item.record ?? null, item.rows[0])
  const params = new URLSearchParams({ tab: 'structured', table: item.table_name })
  if (key) {
    params.set('col', key.column)
    params.set('val', key.value)
  }
  return `/workspace/data?${params.toString()}`
}

export function documentHitPath(hit: DocumentHit): string {
  const params = new URLSearchParams({
    tab: 'documents',
    doc: String(hit.document_id),
  })
  if (hit.page != null && hit.page > 0) {
    params.set('page', String(hit.page))
  }
  const passage = hit.passage?.trim()
  if (passage) {
    params.set('passage', passage.slice(0, 400))
  }
  return `/workspace/data?${params.toString()}`
}

export function parseDataExplorerSearch(search: string): {
  tab: 'structured' | 'documents'
  structured?: StructuredDeepLink & { table: string }
  document?: DocumentDeepLink
} {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const tab = params.get('tab') === 'documents' ? 'documents' : 'structured'
  const table = params.get('table')?.trim()
  const col = params.get('col')?.trim()
  const val = params.get('val')?.trim()
  const docRaw = params.get('doc')
  const passage = params.get('passage')?.trim()
  const pageRaw = params.get('page')

  let structured: (StructuredDeepLink & { table: string }) | undefined
  if (table && col && val) {
    structured = { table, column: col, value: val }
  }

  const page =
    pageRaw && /^\d+$/.test(pageRaw) ? Number(pageRaw) : undefined
  const document =
    docRaw && /^\d+$/.test(docRaw)
      ? { documentId: Number(docRaw), passage: passage || undefined, page }
      : undefined

  return { tab, structured, document }
}
