import {
  ClipboardList,
  FileSearch,
  PackageSearch,
  ShieldCheck,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import type { AgentCapability } from '../../api/types'
import { useAuth } from '../../context/AuthContext'
import { DEFAULT_AGENT_CAPABILITIES } from '../../lib/agentCapabilities'
import { WORKSPACE_CARD_COPY } from '../../lib/workspaceStarters'

const CAPABILITY_ICONS: Record<string, LucideIcon> = {
  investigate: ShieldCheck,
  lookup: PackageSearch,
  documents: FileSearch,
  recovery: Wrench,
  actions: ClipboardList,
}

function SkeletonCard() {
  return (
    <li
      className="min-h-[8.75rem] animate-pulse rounded-xl bg-stone-100/90 ring-1 ring-stone-200/50 motion-reduce:animate-none"
      aria-hidden
    />
  )
}

function mergeWithDisplayCopy(caps: AgentCapability[]): AgentCapability[] {
  return caps.map((cap) => {
    const copy = WORKSPACE_CARD_COPY[cap.id]
    if (!copy) return cap
    return { ...cap, description: copy.blurb }
  })
}

export function AgentGuide({
  onTryExample,
}: {
  onTryExample: (prompt: string, returnId?: string | null) => void
}) {
  const { isAuthenticated } = useAuth()
  const [items, setItems] = useState<AgentCapability[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) {
      setItems(DEFAULT_AGENT_CAPABILITIES)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    api
      .agentCapabilities()
      .then((caps) => {
        if (!cancelled) setItems(mergeWithDisplayCopy(caps))
      })
      .catch(() => {
        if (!cancelled) setItems(mergeWithDisplayCopy(DEFAULT_AGENT_CAPABILITIES))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  const display = useMemo(() => items.slice(0, 4), [items])

  return (
    <section aria-labelledby="agent-guide-title">
      <div className="mb-2.5 flex items-baseline justify-between gap-2 px-0.5">
        <h2
          id="agent-guide-title"
          className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500"
        >
          Suggested workflows
        </h2>
        <span className="text-[11px] text-stone-400">Select to start</span>
      </div>

      <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 sm:gap-3">
        {loading && Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)}
        {!loading &&
          display.map((cap) => {
            const Icon = CAPABILITY_ICONS[cap.id] ?? ShieldCheck
            const copy = WORKSPACE_CARD_COPY[cap.id]
            const exampleLabel = copy?.exampleLabel ?? cap.example_prompt
            return (
              <li key={cap.id} className="min-h-0">
                <button
                  type="button"
                  onClick={() => onTryExample(cap.example_prompt, cap.return_id_hint)}
                  className="group flex h-full min-h-[8.75rem] w-full flex-col rounded-xl border border-stone-200/90 bg-white p-3.5 text-left shadow-card transition-[border-color,box-shadow] hover:border-accent-200/80 hover:shadow-elevated focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600 sm:p-4"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-700 ring-1 ring-accent-100/90"
                      aria-hidden
                    >
                      <Icon className="size-4" strokeWidth={1.75} />
                    </span>
                    {cap.return_id_hint && (
                      <span className="rounded-md bg-stone-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-stone-600 ring-1 ring-stone-200/80">
                        {cap.return_id_hint}
                      </span>
                    )}
                  </div>

                  <span className="mt-3 text-sm font-semibold leading-snug text-stone-900">
                    {cap.title}
                  </span>

                  <p className="mt-2 flex-1 text-xs leading-relaxed text-stone-600 sm:text-[13px] sm:leading-5">
                    {cap.description}
                  </p>

                  <p className="mt-2.5 border-t border-stone-100 pt-2 text-[11px] font-medium text-accent-800/90 group-hover:text-accent-700">
                    {exampleLabel}
                  </p>
                </button>
              </li>
            )
          })}
      </ul>
    </section>
  )
}
