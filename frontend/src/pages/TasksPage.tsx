import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { RecoveryTaskOut } from '../api/types'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useLiveResource } from '../hooks/useLiveResource'
import { humanize } from '../lib/format'
import { button, panelTitle } from '../components/ui/styles'

export function TasksPage() {
  const { username } = useAuth()
  const { showToast } = useToast()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [busyId, setBusyId] = useState<number | null>(null)

  const { data, loading, refresh } = useLiveResource<RecoveryTaskOut[]>(
    () => api.listRecoveryTasks(statusFilter ? { status: statusFilter } : undefined),
    [statusFilter],
  )

  async function patchTask(taskId: number, patch: { assigned_to?: string; task_status?: string }) {
    setBusyId(taskId)
    try {
      await api.patchRecoveryTask(taskId, patch)
      refresh()
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="workspace-shell flex min-h-dvh flex-col">
      <WorkspaceNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        <h1 className={panelTitle}>Recovery tasks</h1>
        <p className="mt-2 text-sm text-stone-600">
          Assign and complete warehouse recovery work.{' '}
          <Link to="/workspace" className="text-accent-700 underline-offset-2 hover:underline">
            Back to agent
          </Link>
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <label className="text-sm text-stone-600">
            Status
            <select
              className="ml-2 rounded-md border border-stone-200 bg-white px-2 py-1 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All open</option>
              <option value="pending">Pending</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
            </select>
          </label>
        </div>

        {loading && !data && (
          <div className="mt-8 flex items-center gap-2 text-sm text-stone-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading…
          </div>
        )}

        <ul className="mt-6 divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
          {(data ?? []).length === 0 && !loading && (
            <li className="px-4 py-6 text-sm text-stone-500">No tasks match this filter.</li>
          )}
          {(data ?? []).map((task) => (
            <li key={task.recovery_task_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-mono text-sm font-medium text-stone-900">{task.return_id}</p>
                <p className="text-sm text-stone-600">
                  {humanize(task.recovery_method)} · {humanize(task.task_status)}
                  {task.assigned_to ? ` · ${task.assigned_to}` : ''}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {!task.assigned_to && username && (
                  <button
                    type="button"
                    className={button('secondary', 'sm')}
                    disabled={busyId === task.recovery_task_id}
                    onClick={() => patchTask(task.recovery_task_id, { assigned_to: username })}
                  >
                    Assign to me
                  </button>
                )}
                {task.task_status !== 'in_progress' && task.task_status !== 'completed' && (
                  <button
                    type="button"
                    className={button('secondary', 'sm')}
                    disabled={busyId === task.recovery_task_id}
                    onClick={() => patchTask(task.recovery_task_id, { task_status: 'in_progress' })}
                  >
                    Start
                  </button>
                )}
                {task.task_status !== 'completed' && (
                  <button
                    type="button"
                    className={button('primary', 'sm')}
                    disabled={busyId === task.recovery_task_id}
                    onClick={() => patchTask(task.recovery_task_id, { task_status: 'completed' })}
                  >
                    Complete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </main>
    </div>
  )
}
