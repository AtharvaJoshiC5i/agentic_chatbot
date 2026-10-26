import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { CaseOut } from '../../api/types'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { button } from '../ui/styles'

export function ContextPanelWorkflow({
  returnId,
  onChanged,
}: {
  returnId: string
  onChanged?: () => void
}) {
  const { role, username } = useAuth()
  const { showToast } = useToast()
  const [caseRow, setCaseRow] = useState<CaseOut | null>(null)
  const [busy, setBusy] = useState(false)

  const isSupervisor = role?.includes('supervisor')
  const isWarehouse = role?.includes('warehouse')

  useEffect(() => {
    api
      .listCases()
      .then((res) => {
        const open = res.items.find(
          (c) =>
            c.return_id === returnId &&
            c.case_status !== 'resolved' &&
            c.case_status !== 'closed',
        )
        setCaseRow(open ?? null)
      })
      .catch(() => setCaseRow(null))
  }, [returnId])

  async function run<T>(fn: () => Promise<T>) {
    setBusy(true)
    try {
      await fn()
      onChanged?.()
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Workflow</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {isSupervisor && caseRow && (
          <>
            <button
              type="button"
              className={button('secondary', 'sm')}
              disabled={busy}
              onClick={() =>
                run(async () => {
                  if (!username) return
                  await api.assignCase(caseRow.case_id, username)
                })
              }
            >
              Assign case to me
            </button>
            <button
              type="button"
              className={button('primary', 'sm')}
              disabled={busy}
              onClick={() => run(() => api.resolveCase(caseRow.case_id, 'Resolved from context panel'))}
            >
              Resolve case
            </button>
          </>
        )}
        {isSupervisor && (
          <button
            type="button"
            className={button('secondary', 'sm')}
            disabled={busy}
            onClick={() => run(() => api.closeReturn(returnId))}
          >
            Close return
          </button>
        )}
        {(isWarehouse || isSupervisor) && (
          <button
            type="button"
            className={button('primary', 'sm')}
            disabled={busy}
            onClick={() =>
              run(() =>
                api.recordInspection(returnId, {
                  product_condition: 'good',
                  inspection_result: 'pass',
                  accessories_complete: true,
                  defect_verified: false,
                  inspector_notes: 'Recorded from workspace context panel',
                }),
              )
            }
          >
            Record inspection
          </button>
        )}
      </div>
    </section>
  )
}
