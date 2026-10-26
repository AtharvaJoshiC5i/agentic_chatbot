import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  clearAuth,
  getStoredRole,
  getStoredToken,
  getStoredUsername,
  isAccessTokenExpired,
  resetUnauthorizedGuard,
  setAuth,
  setOnUnauthorized,
} from '../api/client'
import { ApiError } from '../api/types'

type AuthState = {
  token: string | null
  role: string | null
  username: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

function readInitialAuth(): {
  token: string | null
  role: string | null
  username: string | null
} {
  const token = getStoredToken()
  if (!token || isAccessTokenExpired(token)) {
    if (token) clearAuth()
    return { token: null, role: null, username: null }
  }
  const username = getStoredUsername()
  return {
    token,
    role: getStoredRole(),
    username: username?.trim() ? username.trim() : null,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const initial = readInitialAuth()
  const [token, setToken] = useState<string | null>(initial.token)
  const [role, setRole] = useState<string | null>(initial.role)
  const [username, setUsername] = useState<string | null>(initial.username)

  useEffect(() => {
    if (username?.trim()) return
    const u = getStoredUsername()
    if (u) setUsername(u)
  }, [username])

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setRole(null)
    setUsername(null)
  }, [])

  useEffect(() => {
    setOnUnauthorized(() => {
      logout()
      navigate('/login', { replace: true, state: { reason: 'session_expired' } })
    })
    return () => setOnUnauthorized(null)
  }, [logout, navigate])

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'shopsphere_access_token' && !e.newValue) logout()
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [logout])

  const login = useCallback(async (loginUsername: string, password: string) => {
    try {
      const res = await api.login(loginUsername, password)
      const resolvedUsername = res.username?.trim() || loginUsername.trim()
      setAuth(res.access_token, res.role, resolvedUsername)
      resetUnauthorizedGuard()
      setToken(res.access_token)
      setRole(res.role)
      setUsername(resolvedUsername)
    } catch (e) {
      if (e instanceof ApiError) throw e
      throw new Error('Login failed', { cause: e })
    }
  }, [])

  const isAuthenticated = Boolean(
    token && getStoredToken() === token && !isAccessTokenExpired(token),
  )

  const value = useMemo(
    () => ({
      token,
      role,
      username,
      isAuthenticated,
      login,
      logout,
    }),
    [token, role, username, isAuthenticated, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
