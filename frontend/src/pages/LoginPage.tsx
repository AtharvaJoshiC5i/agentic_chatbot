import { Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/types'
import { RoleLandingPanel, RolePill } from '../components/landing/RoleLandingPanel'
import { BrandMark } from '../components/ui/BrandMark'
import { button, fieldInput, fieldLabel } from '../components/ui/styles'
import { useAuth } from '../context/AuthContext'
import {
  DEMO_ACCOUNTS,
  demoAccountForPersona,
  parsePersonaIdParam,
} from '../lib/demoAccounts'
import { workspacePersonaById, type WorkspacePersonaId } from '../lib/personaWorkspace'

export function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()

  const from = (location.state as { from?: string; reason?: string } | null)?.from ?? '/workspace'
  const sessionExpired =
    (location.state as { reason?: string } | null)?.reason === 'session_expired'

  const roleFromUrl = parsePersonaIdParam(searchParams.get('role'))
  const [personaId, setPersonaId] = useState<WorkspacePersonaId>(
    roleFromUrl ?? 'returns_analyst',
  )

  const account = useMemo(() => demoAccountForPersona(personaId), [personaId])
  const persona = useMemo(() => workspacePersonaById(personaId), [personaId])

  const [username, setUsername] = useState(account.username)
  const [password, setPassword] = useState(account.password)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (roleFromUrl && roleFromUrl !== personaId) {
      setPersonaId(roleFromUrl)
    }
  }, [roleFromUrl, personaId])

  useEffect(() => {
    setUsername(account.username)
    setPassword(account.password)
  }, [account.username, account.password])

  function selectRole(id: WorkspacePersonaId) {
    setPersonaId(id)
    setSearchParams({ role: id }, { replace: true })
    setError(null)
  }

  const roleHome =
    personaId === 'returns_analyst' ||
    personaId === 'warehouse_manager' ||
    personaId === 'returns_supervisor'
      ? '/workspace/dashboard'
      : '/workspace'

  if (isAuthenticated) {
    return <Navigate to={roleHome} replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
      const dest =
        from === '/workspace' &&
        personaId === 'returns_analyst' ||
        personaId === 'warehouse_manager' ||
        personaId === 'returns_supervisor'
          ? '/workspace/dashboard'
          : from
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[var(--color-canvas)] lg:flex-row">
      <aside className="border-b border-stone-200 px-6 py-10 lg:w-[min(42rem,46%)] lg:border-b-0 lg:border-r lg:px-12 lg:py-16">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-stone-500 transition-colors hover:text-stone-800"
        >
          <BrandMark className="size-7 rounded-lg shadow-sm" tone="brand" />
          <span className="font-medium text-stone-800">ShopSphere</span>
        </Link>

        <div className="mt-10 lg:mt-14">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Demo role">
            {DEMO_ACCOUNTS.map((a) => (
              <RolePill
                key={a.personaId}
                label={workspacePersonaById(a.personaId).shortName}
                active={a.personaId === personaId}
                onClick={() => selectRole(a.personaId)}
              />
            ))}
          </div>

          <div className="mt-10">
            <RoleLandingPanel persona={persona} />
          </div>
        </div>
      </aside>

      <main className="flex flex-1 items-center justify-center px-6 py-12 lg:px-12">
        <div className="w-full max-w-[22rem]">
          <h1 className="text-xl font-semibold tracking-tight text-stone-900">Sign in</h1>
          <p className="mt-1.5 text-sm text-stone-500">
            Demo credentials for <span className="font-medium text-stone-700">{persona.shortName}</span>
            .
          </p>

          {sessionExpired && (
            <p
              className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
              role="status"
            >
              Your session expired. Sign in again to continue.
            </p>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className={fieldLabel} htmlFor="username">
                Username
              </label>
              <input
                id="username"
                className={fieldInput}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className={fieldLabel} htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className={fieldInput}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <p
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
                role="alert"
              >
                {error}
              </p>
            )}

            <button type="submit" disabled={submitting} className={`${button('primary', 'md')} w-full`}>
              {submitting && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {submitting ? 'Signing in…' : 'Enter workspace'}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-stone-400">
            <Link to="/" className="text-stone-500 underline-offset-2 hover:text-stone-700 hover:underline">
              Choose a different role
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
