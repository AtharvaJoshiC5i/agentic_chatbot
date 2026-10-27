/** Dashboard → agent navigation and stage prompts aligned with docs/WORKFLOW.md */

import type { WorkspaceQueueItem } from '../api/types'

export const WORKFLOW_PIPELINE =
  'Policy check → inspection case → warehouse inspect & verdict → submit refund/replacement → supervisor approval → customer message'

export function agentPath(returnId: string): string {
  return `/workspace?return=${encodeURIComponent(returnId.trim().toUpperCase())}`
}

export type AgentNavTarget = {
  to: string
  state: { draftMessage: string }
}

export function agentNav(returnId: string, draftMessage: string): AgentNavTarget {
  return {
    to: agentPath(returnId),
    state: { draftMessage: draftMessage.trim() },
  }
}

export function analystAgentPrompt(
  stage: string | null | undefined,
  resolution: string | null | undefined,
): string {
  switch (stage) {
    case 'investigate':
      return (
        'Investigate this return against company refund and replacement policy (policy documents and structured records). ' +
        'Compare what the customer claimed with what policy allows. ' +
        'If the request clearly falls outside policy, explain the evidence, decline the return with the policy basis, and ensure a customer email draft is created—do not open a warehouse inspection case. ' +
        'If the request is within policy for the requested resolution, open an inspection case so the warehouse manager can inspect the unit (the system assigns them automatically). ' +
        'Do not submit a refund or replacement to the supervisor yet.'
      )
    case 'await_warehouse':
      return (
        'Call get_return_workflow_status for this return. Summarize whether the warehouse has received the unit, completed inspection, and recorded a verdict. ' +
        'I can only submit to the supervisor after a proceed verdict that matches the customer request type. Do not open a duplicate case.'
      )
    case 'decline_request':
      return (
        'The warehouse verdict says this refund or replacement cannot be performed. Summarize their reason, then ask me to confirm before you decline the return request with that reason so a customer email draft is created.'
      )
    case 'submit_refund':
      return (
        'Using inspection results and calculate_refundable_amount, submit a refund request for supervisor approval. Do not approve payout yourself.'
      )
    case 'submit_replacement':
      return (
        'Using inspection results and return details, submit a replacement request for supervisor approval. Do not approve dispatch yourself.'
      )
    case 'await_supervisor':
      return `What is the status of my pending supervisor approval for this return (${resolution ?? 'refund or replacement'})?`
    case 'customer_follow_up':
      return (
        'Call list_customer_notifications for this return and show the drafted customer email. ' +
        'After I confirm the wording, record message confirmation with send_customer_notification to close the case. This demo does not send real email.'
      )
    default:
      return 'Summarize this return, where it sits in the returns workflow, and the single next action I should take.'
  }
}

export function warehouseAgentPrompt(row: WorkspaceQueueItem): string {
  const rid = row.return_id ?? ''
  const resolution = row.requested_resolution ?? 'refund or replacement'
  if (row.workflow_stage === 'receive') {
    return (
      `Use get_warehouse_handoff_status for ${rid}. Analyst case #${row.case_id ?? '—'}; customer requested ${resolution}. ` +
      'Confirm physical receipt before inspection. After receipt, inspect the unit, then record whether the refund or replacement can be performed.'
    )
  }
  if (row.workflow_stage === 'verdict') {
    return (
      `Use get_warehouse_handoff_status for ${rid}. Inspection is on file for ${resolution}. ` +
      'Tell me if it can be performed (check stock for replacements), then record my verdict with record_warehouse_verdict. A decline requires a reason for the analyst.'
    )
  }
  return (
    `Use get_warehouse_handoff_status for ${rid}. Customer requested ${resolution}. ` +
    'Guide receipt → inspection → verdict for the returns analyst. Do not approve refund or replacement yourself.'
  )
}

export function supervisorAgentPrompt(row: WorkspaceQueueItem): string {
  const rid = row.return_id ?? ''
  const kind = row.approval_kind ?? row.action_type ?? 'request'
  return (
    `Use build_return_timeline_tool and get_return_workflow_status for ${rid}. ` +
    `Review the full investigation and inspection history, then summarize whether to approve or reject the pending ${kind} request. ` +
    'If I decide in chat, use the correct approve tool for refunds, replacements, or action requests. The returns analyst will confirm the customer email afterward.'
  )
}

export function genericAgentPrompt(returnId: string, stage?: string | null): string {
  if (stage) return analystAgentPrompt(stage, null)
  return `Summarize return ${returnId} and the next step in the governed returns workflow.`
}
