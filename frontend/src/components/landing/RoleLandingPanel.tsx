import { ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'
import type { WorkspacePersona } from '../../lib/personaWorkspace'
import { button } from '../ui/styles'

export function RoleLandingPanel({
  persona,
  children,
}: {
  persona: WorkspacePersona
  children?: ReactNode
}) {
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <p className="text-xs font-medium tracking-wide text-stone-500 uppercase">{persona.eyebrow}</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-balance text-stone-900 sm:text-4xl">
          {persona.headline}
        </h1>
        <p className="mt-4 max-w-md text-base leading-relaxed text-stone-600">{persona.landingEssence}</p>
        <ul className="mt-8 space-y-3 border-t border-stone-200 pt-8" aria-label="What you can do">
          {persona.permissionHints.map((hint) => (
            <li key={hint} className="flex gap-3 text-sm text-stone-700">
              <span className="mt-2 size-1 shrink-0 rounded-full bg-accent-600" aria-hidden />
              <span>{hint}</span>
            </li>
          ))}
        </ul>
      </div>
      {children}
    </div>
  )
}

export function RoleCard({
  persona,
  active,
}: {
  persona: WorkspacePersona
  active?: boolean
}) {
  return (
    <div
      className={`group flex h-full flex-col rounded-xl border px-5 py-5 transition-colors ${
        active
          ? 'border-accent-600/40 bg-white shadow-subtle'
          : 'border-stone-200 bg-white/80 hover:border-stone-300 hover:bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-stone-900">{persona.shortName}</p>
        <ArrowRight
          className="size-4 shrink-0 text-stone-400 transition-transform group-hover:translate-x-0.5 group-hover:text-accent-700"
          strokeWidth={1.75}
          aria-hidden
        />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">{persona.landingEssence}</p>
    </div>
  )
}

export function RolePill({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
        active
          ? 'bg-stone-900 text-white'
          : 'bg-white text-stone-600 ring-1 ring-stone-200 hover:bg-stone-50'
      }`}
    >
      {label}
    </button>
  )
}

export function SignInCta({ to }: { to: string }) {
  return (
    <a href={to} className={`${button('primary', 'lg')} mt-10 inline-flex w-full sm:w-auto`}>
      Continue to sign in
      <ArrowRight className="size-4" aria-hidden />
    </a>
  )
}
