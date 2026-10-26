import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    const from = location.pathname === '/login' ? '/workspace' : location.pathname
    return <Navigate to="/login" replace state={{ from }} />
  }

  return children
}
