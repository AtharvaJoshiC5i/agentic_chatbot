import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { ReturnWorkflowOut } from '../../api/types'
import { humanize } from '../../lib/format'

export function ContextPanelWorkflow({
  returnId,
  refreshKey = 0,
}: {
  returnId: string
  refreshKey?: number
}) {
  const [workflow, setWorkflow] = useState<ReturnWorkflowOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const requestSeq = useRef(0)

  useEffect(() => {
    const seq = ++requestSeq.current
    let cancelled = false
    const hasData = workflow !== null
    if (!hasData) setLoading(true)
    else setRefreshing(true)

    api
      .getReturnWorkflow(returnId)
      .then((data) => {
        if (cancelled || seq !== requestSeq.current) return
        setWorkflow(data)
      })
      .catch(() => {
        if (cancelled || seq !== requestSeq.current) return
        setWorkflow(null)
      })
      .finally(() => {
        if (cancelled || seq !== requestSeq.current) return
        setLoading(false)
        setRefreshing(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refreshKey triggers refetch; workflow read only for initial UX
  }, [returnId, refreshKey])

  if (loading && !workflow) {
    return <p className="text-xs text-stone-500">Loading workflow status…</p>
  }

  if (!workflow) {
    return <p className="text-xs text-stone-500">Workflow status unavailable.</p>
  }

  return (
    <section aria-live="polite">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Workflow status</h3>
        {refreshing && (
          <span className="text-[10px] text-stone-400">Updating…</span>
        )}
      </div>
      <p className="mt-2 text-sm leading-relaxed text-stone-700">{workflow.status_summary}</p>
      <dl className="mt-3 space-y-2 text-xs text-stone-600">
        {workflow.analyst_workflow_stage && (
          <div>
            <dt className="font-medium text-stone-500">Analyst step</dt>
            <dd>{workflow.analyst_workflow_stage_label ?? humanize(workflow.analyst_workflow_stage)}</dd>
          </div>
        )}
        {workflow.warehouse_queue_stage && (
          <div>
            <dt className="font-medium text-stone-500">Warehouse step</dt>
            <dd>{humanize(workflow.warehouse_queue_stage)}</dd>
          </div>
        )}
        {workflow.next_owner && (
          <div>
            <dt className="font-medium text-stone-500">Next owner</dt>
            <dd>{humanize(workflow.next_owner)}</dd>
          </div>
        )}
      </dl>
      <p className="mt-3 text-[11px] text-stone-400">
        Complete actions from your queue or use Ask agent for guided steps.
      </p>
    </section>
  )
}
