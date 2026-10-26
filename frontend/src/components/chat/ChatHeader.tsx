import { PanelLeftClose, PanelLeftOpen, PanelRight, SquarePen } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { workspacePersonaForRole } from '../../lib/personaWorkspace'
import { workspaceIconButton } from '../ui/styles'

export function ChatHeader({
  sidebarOpen,
  onToggleSidebar,
  onNewChat,
  returnId,
  contextOpen,
  onToggleContext,
}: {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  onNewChat: () => void
  returnId: string | null
  contextOpen: boolean
  onToggleContext: () => void
}) {
  const { role } = useAuth()
  const persona = workspacePersonaForRole(role)

  return (
    <header className="workspace-header flex h-14 shrink-0 items-center gap-1.5 px-3 sm:gap-2 sm:px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        className={workspaceIconButton}
        aria-expanded={sidebarOpen}
        aria-controls="workspace-sidebar"
        aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
      >
        {sidebarOpen ? (
          <PanelLeftClose className="size-[18px]" strokeWidth={1.75} />
        ) : (
          <PanelLeftOpen className="size-[18px]" strokeWidth={1.75} />
        )}
      </button>
      <button
        type="button"
        className={`${workspaceIconButton} hidden sm:inline-flex`}
        onClick={onNewChat}
        aria-label="New conversation"
      >
        <SquarePen className="size-4" strokeWidth={1.75} />
      </button>

      <div className="flex min-w-0 flex-1 items-center gap-2 border-l border-stone-200/80 pl-2.5 sm:pl-3">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold text-stone-900">
            {persona.headerTitle}
          </h1>
          <p className="hidden truncate text-xs text-stone-500 sm:block">{persona.headerTagline}</p>
        </div>
      </div>

      {returnId && (
        <button
          type="button"
          onClick={onToggleContext}
          aria-pressed={contextOpen}
          className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors ${
            contextOpen
              ? 'border-stone-300 bg-stone-100 text-stone-900'
              : 'border-stone-200 bg-white text-stone-700 hover:bg-stone-50'
          }`}
        >
          <PanelRight className="size-3.5 text-stone-500" strokeWidth={1.75} aria-hidden />
          <span className="font-mono text-[11px] font-semibold tracking-wide">{returnId}</span>
        </button>
      )}
    </header>
  )
}
