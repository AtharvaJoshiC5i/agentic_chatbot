import type { WorkspacePersona } from '../../lib/personaWorkspace'

export function RoleLandingPanel({ persona }: { persona: WorkspacePersona }) {
  return (
    <div className="mt-10">
      <p className="text-xs font-medium tracking-wide text-stone-500 uppercase">{persona.eyebrow}</p>
      <p className="mt-3 text-lg font-semibold text-stone-900">{persona.shortName}</p>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-stone-600">{persona.headerTagline}</p>
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
