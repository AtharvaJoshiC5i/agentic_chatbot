import type { WorkspaceDashboardOut } from '../../api/types'

const LABELS: Record<WorkspaceDashboardOut['persona'], Record<string, string>> = {
  returns_analyst: {
    queue_total: 'In your queue',
    your_move: 'Your move',
    to_decline: 'To decline',
    needs_investigation: 'Needs investigation',
    awaiting_warehouse: 'With warehouse',
    ready_for_supervisor: 'Ready to submit',
    pending_supervisor: 'With supervisor',
    customer_follow_up: 'Email customer',
  },
  warehouse_manager: {
    queue_total: 'In your queue',
    awaiting_receipt: 'Awaiting receipt',
    awaiting_inspection: 'Awaiting inspection',
    awaiting_verdict: 'Awaiting your verdict',
  },
  returns_supervisor: {
    queue_total: 'Pending approvals',
    pending_refunds: 'Refund requests',
    pending_replacements: 'Replacement requests',
  },
}

export function kpiLabel(persona: WorkspaceDashboardOut['persona'], key: string): string {
  return LABELS[persona][key] ?? key.replace(/_/g, ' ')
}
