import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { BrandLockup } from '../ui/BrandMark'
import { button, container } from '../ui/styles'

export function LandingNav() {
  const { isAuthenticated } = useAuth()

  return (
    <header className="sticky top-0 z-30 border-b border-stone-200/80 bg-[var(--color-canvas)]/90 backdrop-blur-md">
      <div className={`${container} flex h-14 items-center justify-between gap-6`}>
        <Link to="/" aria-label="ShopSphere home">
          <BrandLockup />
        </Link>

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <Link to="/workspace" className={button('primary', 'sm')}>
              Workspace
            </Link>
          ) : (
            <Link to="/login" className={button('primary', 'sm')}>
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
