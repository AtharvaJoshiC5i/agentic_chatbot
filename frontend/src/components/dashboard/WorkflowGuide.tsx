import { WORKFLOW_PIPELINE } from '../../lib/workflowAgent'
import { useAuth } from '../../context/AuthContext'

export function WorkflowGuide() {
  const { role } = useAuth()
  const isAnalyst = Boolean(role?.includes('analyst') && !role?.includes('supervisor'))
  const isWarehouse = Boolean(role?.includes('warehouse'))
  const isSupervisor = Boolean(role?.includes('supervisor'))

  const line = isAnalyst
    ? 'You: check policy → open inspection or decline with customer email → after warehouse verdict, submit refund/replacement → confirm customer message after supervisor decision.'
    : isWarehouse
      ? 'You: receive the unit, inspect it, and tell the analyst whether refund or replacement can be performed.'
      : isSupervisor
        ? 'You: review the full timeline and approve or reject the analyst’s refund or replacement request; the analyst emails the customer.'
        : WORKFLOW_PIPELINE

  return (
    <p className="text-xs leading-relaxed text-stone-500">{line}</p>
  )
}
