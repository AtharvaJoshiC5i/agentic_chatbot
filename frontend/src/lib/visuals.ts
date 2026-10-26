/** Visual specs returned by the chat API (`visuals`). Built server-side from SQLite, never from model text. */

export type InvestigationVisual = {
  type: 'investigation'
  return_id: string
  outcome: string
  signal: string
  recommended_actions: string[]
  checks: { title: string; status: string; summary: string }[]
  source: string
}

export type ReturnWindowVisual = {
  type: 'return_window'
  return_id: string
  days_after_delivery: number | null
  window_days: number | null
  within_window: boolean | null
  category: string | null
  delivered: string | null
  requested: string | null
  warranty_months: number | null
  within_warranty: boolean | null
  source: string
}

export type EvidenceVisual = {
  type: 'evidence'
  return_id: string
  purchased_serial: string | null
  inspections: {
    inspection_id: number
    date: string
    returned_serial: string | null
    serial_match: boolean | null
    condition: string
    defect_verified: boolean
    accessories_complete: boolean
    result: string
  }[]
  source: string
}

export type RecoveryVisual = {
  type: 'recovery'
  return_id: string
  unsafe: boolean
  recommended_method: string | null
  requires_approval: boolean
  rationale: string
  options: { method: string; net_inr: number; feasibility: string; eligible: boolean; reason: string | null }[]
  source: string
}

export type RefundLedgerVisual = {
  type: 'refund_ledger'
  return_id: string
  has_completed: boolean
  refunds: { refund_id: number; amount_inr: number; status: string; approval: string; processed: string | null }[]
  source: string
}

export type ActionsVisual = {
  type: 'actions'
  return_id: string
  actions: { action_id: number; action_type: string; requested_by: string; approval: string; execution: string }[]
  source: string
}

export type RefundQueueVisual = {
  type: 'refund_queue'
  count: number
  total_inr: number
  rows: { refund_id: number; return_id: string; amount_inr: number }[]
  thresholds_inr: { analyst: number; supervisor: number }
  source: string
}

export type CaseQueueVisual = {
  type: 'case_queue'
  count: number
  overdue: number
  rows: { case_id: number; return_id: string; issue_type: string; priority: string; status: string; assigned_to: string | null; due: string | null; overdue: boolean }[]
  source: string
}

export type WorkflowVisual = {
  type: 'workflow'
  return_id: string
  status_summary: string
  warehouse_work_complete: boolean
  inspection_count: number
  analyst_workflow_stage: string | null
  analyst_next_action: string | null
  active_case: { case_id: number; case_status: string; issue_type: string; priority: string } | null
  source: string
}

export type ChatVisual =
  | InvestigationVisual
  | ReturnWindowVisual
  | WorkflowVisual
  | EvidenceVisual
  | RecoveryVisual
  | RefundLedgerVisual
  | ActionsVisual
  | RefundQueueVisual
  | CaseQueueVisual

export function humanizeCode(value: string | null | undefined): string {
  if (!value) return '—'
  const text = value.replace(/_/g, ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function formatInr(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value)
}
