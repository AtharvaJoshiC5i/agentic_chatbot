import { Link } from 'react-router-dom'
import type { WorkspacePersona } from '../../lib/personaWorkspace'

export function DashboardStarterCards({ persona }: { persona: WorkspacePersona }) {
  const starters = persona.starters.slice(0, 3)

  return (
    <section aria-labelledby="dashboard-starters-title">
      <h2 id="dashboard-starters-title" className="text-sm font-semibold text-stone-900">
        Suggested next steps
      </h2>
      <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {starters.map((item) => {
          const to = item.return_id_hint
            ? `/workspace?return=${encodeURIComponent(item.return_id_hint)}`
            : '/workspace'
          return (
            <li key={item.id}>
              <Link
                to={to}
                className="flex h-full flex-col rounded-lg border border-stone-200 bg-white px-4 py-3.5 text-left shadow-sm transition-shadow hover:shadow-md"
              >
                {item.return_id_hint && (
                  <span className="font-mono text-[10px] font-medium text-stone-400">
                    {item.return_id_hint}
                  </span>
                )}
                <span className="mt-1 text-sm font-medium text-stone-900">{item.title}</span>
                <p className="mt-0.5 text-xs leading-relaxed text-stone-500">{item.subtitle}</p>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
