import { container } from '../ui/styles'

export function LandingFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-stone-200">
      <div className={`${container} flex flex-col items-center justify-between gap-2 py-8 text-center sm:flex-row sm:text-left`}>
        <p className="text-xs text-stone-500">
          © {year} ShopSphere Retail · Demonstration environment
        </p>
        <p className="text-xs text-stone-400">Internal use only · Every tool call is visible</p>
      </div>
    </footer>
  )
}
