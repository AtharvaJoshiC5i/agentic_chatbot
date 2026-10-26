import { Navigate, Link } from 'react-router-dom'
import { LandingFooter } from '../components/landing/LandingFooter'
import { LandingNav } from '../components/landing/LandingNav'
import { RoleCard } from '../components/landing/RoleLandingPanel'
import { container, eyebrow } from '../components/ui/styles'
import { LANDING_ROLE_ORDER } from '../lib/demoAccounts'
import { workspacePersonaById } from '../lib/personaWorkspace'
import { useAuth } from '../context/AuthContext'

export function LandingPage() {
  const { isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/workspace" replace />
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[var(--color-canvas)]">
      <LandingNav />

      <main className="flex-1">
        <section className={`${container} py-16 sm:py-20 lg:py-24`}>
          <div className="mx-auto max-w-2xl text-center">
            <p className={eyebrow}>ShopSphere internal</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-balance text-stone-900 sm:text-5xl">
              Returns intelligence, role by role.
            </h1>
            <p className="mx-auto mt-5 max-w-lg text-base leading-relaxed text-stone-600">
              Choose the workspace that matches your job. Each profile sees only what you need to
              investigate, explain, recover, or approve—with every tool call visible.
            </p>
          </div>

          <ul className="mx-auto mt-14 grid max-w-4xl gap-3 sm:grid-cols-2 lg:gap-4">
            {LANDING_ROLE_ORDER.map((id) => {
              const persona = workspacePersonaById(id)
              return (
                <li key={id}>
                  <Link to={`/login?role=${id}`} className="block h-full">
                    <RoleCard persona={persona} />
                  </Link>
                </li>
              )
            })}
          </ul>

          <p className="mx-auto mt-12 max-w-md text-center text-xs leading-relaxed text-stone-500">
            Demonstration environment with seeded scenarios R101–R115. Sign in with the demo account
            for your role on the next screen.
          </p>
        </section>
      </main>

      <LandingFooter />
    </div>
  )
}
