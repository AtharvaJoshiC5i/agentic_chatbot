import {
  Activity,
  ArrowRightLeft,
  BadgeCheck,
  ClipboardList,
  FileSearch,
  Headphones,
  LayoutList,
  PackageSearch,
  ShieldCheck,
  TriangleAlert,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { button } from '../ui/styles'
import {
  workspacePersonaForRole,
  type WorkspaceStarterIcon,
} from '../../lib/personaWorkspace'

const STARTER_ICONS: Record<WorkspaceStarterIcon, LucideIcon> = {
  investigate: ShieldCheck,
  lookup: PackageSearch,
  documents: FileSearch,
  recovery: Wrench,
  actions: ClipboardList,
  approve: BadgeCheck,
  portfolio: LayoutList,
  customer: Headphones,
  safety: TriangleAlert,
  monitoring: Activity,
  timeline: ArrowRightLeft,
}

export function WorkspaceEmptyPane({
  onTryExample,
}: {
  onTryExample: (message: string, returnId?: string | null) => void
}) {
  const { role } = useAuth()
  const persona = workspacePersonaForRole(role)
  const isAnalyst = Boolean(role?.includes('analyst') && !role?.includes('supervisor'))
  const isWarehouse = Boolean(role?.includes('warehouse'))
  const isSupervisor = Boolean(role?.includes('supervisor'))

  if (isAnalyst) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Returns analyst</p>
        <p className="mt-3 text-lg font-medium text-stone-900">Work from your queue</p>
        <p className="mt-2 text-sm leading-relaxed text-stone-600">
          Pick a return to investigate, track warehouse inspection, or submit a refund or replacement request.
        </p>
        <Link to="/workspace/dashboard" className={`${button('primary', 'md')} mt-6`}>
          Open returns queue
        </Link>
      </div>
    )
  }

  if (isWarehouse) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Warehouse manager</p>
        <p className="mt-3 text-lg font-medium text-stone-900">Work from your inspection queue</p>
        <p className="mt-2 text-sm leading-relaxed text-stone-600">
          Receive returns the analyst sent and record inspection — for both refund and replacement requests.
        </p>
        <Link to="/workspace/dashboard" className={`${button('primary', 'md')} mt-6`}>
          Open inspection queue
        </Link>
      </div>
    )
  }

  if (isSupervisor) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Returns supervisor</p>
        <p className="mt-3 text-lg font-medium text-stone-900">Work from your approvals queue</p>
        <p className="mt-2 text-sm leading-relaxed text-stone-600">
          Review analyst refund and replacement requests after warehouse inspection. Approve or reject — the analyst
          notifies the customer.
        </p>
        <Link to="/workspace/dashboard" className={`${button('primary', 'md')} mt-6`}>
          Open approvals queue
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-1">
      <header className="border-b border-stone-200 pb-8 text-center">
        <p className="text-xs font-medium tracking-wide text-stone-500 uppercase">{persona.eyebrow}</p>
        <p className="mt-3 text-lg font-medium tracking-tight text-stone-900 sm:text-xl">
          {persona.landingEssence}
        </p>
        <ul className="mt-5 flex flex-wrap justify-center gap-x-4 gap-y-1" aria-label="Your permissions">
          {persona.permissionHints.map((hint) => (
            <li key={hint} className="text-xs text-stone-500">
              {hint}
            </li>
          ))}
        </ul>
      </header>

      <section className="mt-8" aria-labelledby="workspace-examples-title">
        <h2 id="workspace-examples-title" className="text-center text-xs font-medium text-stone-500 uppercase tracking-wide">
          {persona.examplesLabel}
        </h2>

        <ul className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {persona.starters.map((item) => {
            const Icon = STARTER_ICONS[item.icon] ?? ShieldCheck
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onTryExample(item.example_prompt, item.return_id_hint)}
                  className="flex h-full w-full flex-col rounded-lg border border-stone-200 bg-white px-4 py-3.5 text-left transition-colors hover:border-stone-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Icon className="size-3.5 shrink-0 text-stone-400" strokeWidth={1.75} aria-hidden />
                    {item.return_id_hint && (
                      <span className="font-mono text-[10px] font-medium text-stone-400">
                        {item.return_id_hint}
                      </span>
                    )}
                  </div>
                  <span className="mt-2 text-sm font-medium text-stone-900">{item.title}</span>
                  <p className="mt-0.5 text-xs leading-relaxed text-stone-500">{item.subtitle}</p>
                </button>
              </li>
            )
          })}
        </ul>
      </section>
    </div>
  )
}
