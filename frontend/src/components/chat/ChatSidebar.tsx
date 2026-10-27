import { Database, Inbox, LogOut, PanelLeftClose, Plus, Search, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import type { ReturnSummary } from '../../api/types'
import type { Conversation } from '../../lib/chats'
import { formatRelativeShort, humanize } from '../../lib/format'
import { workspacePersonaForRole } from '../../lib/personaWorkspace'
import { useAuth } from '../../context/AuthContext'
import { BrandMark } from '../ui/BrandMark'
import { button, sidebarSearchInput, sidebarSectionLabel, workspaceIconButton } from '../ui/styles'

const SIDEBAR_WIDTH = 'w-[15.5rem]'

function roleInitial(role: string | null): string {
  if (!role) return 'U'
  return role.trim().charAt(0).toUpperCase()
}

export function ChatSidebar({
  open,
  onToggle,
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onOpenReturn,
  onDeleteConversation,
}: {
  open: boolean
  onToggle: () => void
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNewChat: () => void
  onOpenReturn: (returnId: string) => void
  onDeleteConversation: (id: string) => void
}) {
  const navigate = useNavigate()
  const { role, username, logout } = useAuth()
  const persona = workspacePersonaForRole(role)
  const isAnalyst = Boolean(role?.includes('analyst') && !role?.includes('supervisor'))
  const isWarehouse = Boolean(role?.includes('warehouse'))
  const isSupervisor = Boolean(role?.includes('supervisor'))
  const queueHome = isAnalyst || isWarehouse || isSupervisor
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ReturnSummary[]>([])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const t = setTimeout(() => {
      api
        .listReturns({ limit: 8 })
        .then((res) => {
          const q = query.toUpperCase()
          setResults(
            res.items.filter(
              (r) =>
                r.return_id.includes(q) ||
                r.return_reason.toLowerCase().includes(query.toLowerCase()),
            ),
          )
        })
        .catch(() => setResults([]))
    }, 200)
    return () => clearTimeout(t)
  }, [query])

  const sorted = useMemo(
    () =>
      [...conversations].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
      ),
    [conversations],
  )

  function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    onDeleteConversation(id)
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-stone-900/25 backdrop-blur-[2px] lg:hidden"
          onClick={onToggle}
          aria-hidden
        />
      )}
      <aside
        id="workspace-sidebar"
        inert={!open ? true : undefined}
        className={`chat-sidebar fixed inset-y-0 left-0 z-50 flex ${SIDEBAR_WIDTH} flex-col overflow-hidden transition-transform duration-200 ease-out motion-reduce:transition-none lg:static lg:z-0 lg:shrink-0 ${
          open ? 'translate-x-0 lg:flex' : '-translate-x-full lg:hidden'
        }`}
        aria-label="Workspace navigation"
        aria-hidden={!open}
      >
        <div className={`flex h-full ${SIDEBAR_WIDTH} flex-col`}>
          <header className="shrink-0 border-b border-stone-200/80 px-3 pb-3 pt-3">
            <div className="flex items-center justify-between gap-2">
              <Link
                to="/workspace"
                className="flex min-w-0 flex-1 items-center gap-2 rounded-md outline-offset-2 focus-visible:outline-2 focus-visible:outline-accent-600"
              >
                <BrandMark className="size-7 rounded-md" tone="brand" />
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-semibold leading-tight tracking-tight text-stone-900">
                    ShopSphere
                  </p>
                  <p className="truncate text-[10px] font-medium text-stone-500">Returns workspace</p>
                </div>
              </Link>
              <button
                type="button"
                className={`${workspaceIconButton} lg:hidden`}
                onClick={onToggle}
                aria-label="Close sidebar"
              >
                <PanelLeftClose className="size-4" strokeWidth={1.75} />
              </button>
            </div>
          </header>

          <div className="shrink-0 space-y-2 px-2.5 pt-2.5">
            <button type="button" onClick={onNewChat} className={`${button('primary', 'sm')} w-full text-[13px]`}>
              <Plus className="size-3.5" strokeWidth={2} aria-hidden />
              New conversation
            </button>
            {queueHome && (
              <Link
                to="/workspace/dashboard"
                className={`${button('secondary', 'sm')} w-full border-stone-200/90 bg-white/70 text-[13px]`}
              >
                <Inbox className="size-3.5 text-stone-500" strokeWidth={1.75} aria-hidden />
                {isWarehouse ? 'Inspection queue' : isSupervisor ? 'Approvals queue' : 'Returns queue'}
              </Link>
            )}
            <Link
              to="/workspace/data"
              className={`${button('secondary', 'sm')} w-full border-stone-200/90 bg-white/70 text-[13px]`}
            >
              <Database className="size-3.5 text-stone-500" strokeWidth={1.75} aria-hidden />
              Database
            </Link>

            <div className="relative">
              <label htmlFor="sidebar-return-search" className="sr-only">
                Search returns
              </label>
              <Search
                className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-stone-400"
                strokeWidth={1.75}
                aria-hidden
              />
              <input
                id="sidebar-return-search"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by return ID"
                className={sidebarSearchInput}
              />
              {results.length > 0 && (
                <ul
                  className="absolute inset-x-0 top-full z-10 mt-1 overflow-hidden rounded-md border border-stone-200 bg-white py-1 shadow-card"
                  role="listbox"
                >
                  {results.map((r) => (
                    <li key={r.return_id} role="option">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left text-[13px] hover:bg-stone-50"
                        onClick={() => {
                          onOpenReturn(r.return_id)
                          setQuery('')
                          setResults([])
                        }}
                      >
                        <span className="font-mono text-xs font-semibold text-stone-900">
                          {r.return_id}
                        </span>
                        <span className="truncate text-xs text-stone-500">
                          {humanize(r.return_status)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <nav
            className="chat-sidebar__scroll mt-2.5 min-h-0 flex-1 overflow-y-auto px-1.5 pb-2"
            aria-label="Recent conversations"
          >
            <div className="mb-1.5 flex items-baseline justify-between gap-2 px-0.5">
              <p className={sidebarSectionLabel}>History</p>
              {sorted.length > 0 && (
                <span className="pr-1.5 text-[10px] tabular-nums text-stone-400">{sorted.length}</span>
              )}
            </div>

            {sorted.length === 0 ? (
              <p className="px-2 py-6 text-center text-[12px] leading-relaxed text-stone-500">
                No conversations yet.
                <span className="mt-0.5 block text-[11px] text-stone-400">
                  Open a return from your queue or start a new chat.
                </span>
              </p>
            ) : (
              <ul className="space-y-0.5">
                {sorted.map((c) => {
                  const isActive = c.id === activeId
                  return (
                    <li key={c.id} className="group relative">
                      <button
                        type="button"
                        onClick={() => onSelect(c.id)}
                        title={c.title}
                        aria-current={isActive ? 'true' : undefined}
                        className={`relative flex w-full items-stretch rounded-md py-2 pr-8 pl-2.5 text-left transition-colors ${
                          isActive
                            ? 'bg-stone-100 text-stone-900'
                            : 'text-stone-600 hover:bg-stone-50 hover:text-stone-900'
                        }`}
                      >
                        {isActive && (
                          <span
                            className="absolute bottom-2 left-0 top-2 w-0.5 rounded-full bg-accent-600"
                            aria-hidden
                          />
                        )}
                        <span className="min-w-0 flex-1 pl-0.5">
                          <span className="block truncate text-[12px] font-medium leading-4">
                            {c.title}
                          </span>
                          <span className="mt-0.5 flex flex-wrap items-center gap-1.5">
                            <span className="text-[10px] tabular-nums text-stone-400">
                              {formatRelativeShort(c.updatedAt)}
                            </span>
                            {c.returnId && (
                              <span className="inline-flex rounded px-1 py-px font-mono text-[9px] font-medium text-stone-500">
                                {c.returnId}
                              </span>
                            )}
                          </span>
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => handleDelete(c.id, e)}
                        className="absolute top-1/2 right-1.5 flex size-6 -translate-y-1/2 items-center justify-center rounded text-stone-400 opacity-0 transition-opacity hover:bg-stone-200/70 hover:text-stone-700 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-accent-600"
                        aria-label={`Delete conversation: ${c.title}`}
                      >
                        <Trash2 className="size-3.5" strokeWidth={1.75} />
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </nav>

          <footer className="shrink-0 border-t border-stone-200 bg-stone-50/80 px-2.5 py-2.5">
            <div className="flex items-center gap-2">
              <span
                className="flex size-7 shrink-0 items-center justify-center rounded-full bg-stone-200/80 text-[11px] font-semibold text-stone-700"
                aria-hidden
              >
                {roleInitial(role)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11px] font-semibold leading-tight text-stone-800">
                  {username ? `@${username}` : role ? persona.shortName : 'Signed in'}
                </p>
                <p className="truncate text-[10px] leading-tight text-stone-500">{persona.shortName}</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  logout()
                  navigate('/login', { replace: true })
                }}
                className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-[11px] font-medium text-stone-600 hover:bg-white/80 hover:text-stone-900"
              >
                <LogOut className="size-3.5" strokeWidth={1.75} aria-hidden />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </footer>
        </div>
      </aside>
    </>
  )
}
