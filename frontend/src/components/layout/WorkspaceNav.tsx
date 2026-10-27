import { Database, Inbox, MessageSquare } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { BrandMark } from '../ui/BrandMark'
import { navPill } from '../ui/styles'
import { showsSupervisorApprovalsNav, usesFocusedOpsNav } from '../../lib/personaWorkspace'

export function WorkspaceNav() {
  const { role } = useAuth()
  const location = useLocation()
  const [approvalCount, setApprovalCount] = useState(0)
  const approvalsNav = showsSupervisorApprovalsNav(role)
  const focusedOps = usesFocusedOpsNav(role)
  const onApprovalsDashboard = location.pathname.includes('/workspace/dashboard')

  useEffect(() => {
    if (!approvalsNav || onApprovalsDashboard) return
    let cancelled = false
    const load = () => {
      api
        .workspaceDashboard()
        .then((d) => {
          if (!cancelled && d.persona === 'returns_supervisor') {
            setApprovalCount(d.kpis.queue_total ?? 0)
          }
        })
        .catch(() => {})
    }
    load()
    const timer = window.setInterval(load, 60_000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [approvalsNav, onApprovalsDashboard])

  return (
    <header className="workspace-header flex h-12 shrink-0 items-center gap-4 px-4 sm:px-5">
      <NavLink
        to="/workspace"
        className="flex items-center gap-2 rounded-lg outline-offset-2 focus-visible:outline-2 focus-visible:outline-accent-600"
      >
        <BrandMark className="size-7 rounded-md" tone="brand" />
        <span className="hidden text-sm font-semibold tracking-tight text-stone-900 sm:inline">
          ShopSphere
        </span>
      </NavLink>
      <nav className="flex items-center gap-1" aria-label="Workspace">
        {focusedOps && (
          <NavLink to="/workspace/dashboard" className={({ isActive }) => navPill(isActive)}>
            <Inbox className="size-4" strokeWidth={1.75} aria-hidden />
            {approvalsNav ? 'Approvals' : 'Queue'}
            {approvalsNav && approvalCount > 0 && (
              <span className="ml-1 rounded-full bg-accent-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {approvalCount}
              </span>
            )}
          </NavLink>
        )}
        <NavLink to="/workspace" end className={({ isActive }) => navPill(isActive)}>
          <MessageSquare className="size-4" strokeWidth={1.75} aria-hidden />
          Agent
        </NavLink>
        <NavLink to="/workspace/data" className={({ isActive }) => navPill(isActive)}>
          <Database className="size-4" strokeWidth={1.75} aria-hidden />
          Database
        </NavLink>
      </nav>
    </header>
  )
}
