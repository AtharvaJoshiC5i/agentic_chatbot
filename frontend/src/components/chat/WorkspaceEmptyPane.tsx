import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { WORKFLOW_PIPELINE } from '../../lib/workflowAgent'
import { button } from '../ui/styles'

export function WorkspaceEmptyPane(_props: {
  onTryExample: (message: string, returnId?: string | null) => void
}) {
  const { role } = useAuth()
  const isAnalyst = Boolean(role?.includes('analyst') && !role?.includes('supervisor'))
  const isWarehouse = Boolean(role?.includes('warehouse'))
  const isSupervisor = Boolean(role?.includes('supervisor'))

  const title = isWarehouse
    ? 'Inspection queue'
    : isSupervisor
      ? 'Approvals queue'
      : 'Returns queue'

  const blurb = isAnalyst
    ? 'Open a return from the queue and use Ask agent — each return keeps its own chat thread.'
    : isWarehouse
      ? 'Handoffs appear after the analyst opens an inspection case. Record receipt, inspection, and your verdict.'
      : isSupervisor
        ? 'Approve or reject after reviewing the full timeline; the analyst sends the customer message.'
        : WORKFLOW_PIPELINE

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
      <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Agent workspace</p>
      <p className="mt-3 text-lg font-medium text-stone-900">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">{blurb}</p>
      {(isAnalyst || isWarehouse || isSupervisor) && (
        <Link to="/workspace/dashboard" className={`${button('primary', 'md')} mt-6`}>
          Open {title.toLowerCase()}
        </Link>
      )}
    </div>
  )
}
