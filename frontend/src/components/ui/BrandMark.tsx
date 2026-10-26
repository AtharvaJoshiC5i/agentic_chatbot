export function BrandMark({
  className = 'size-8',
  tone = 'dark',
}: {
  className?: string
  tone?: 'dark' | 'light' | 'brand'
}) {
  const surface =
    tone === 'dark'
      ? 'bg-stone-900 text-white'
      : tone === 'brand'
        ? 'bg-accent-700 text-white'
        : 'bg-white text-stone-900 ring-1 ring-stone-200/90'
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-lg ${surface} ${className}`}
      aria-hidden
    >
      <svg viewBox="0 0 32 32" fill="none" className="size-[58%]">
        <circle cx="16" cy="16" r="8.5" stroke="currentColor" strokeWidth="2" />
        <circle cx="19.5" cy="12.5" r="2.5" fill="currentColor" />
      </svg>
    </span>
  )
}

export function BrandLockup({ tone = 'dark' }: { tone?: 'dark' | 'light' | 'brand' }) {
  const text = tone === 'light' ? 'text-white' : 'text-stone-900'
  return (
    <span className="flex items-center gap-2.5">
      <BrandMark tone={tone === 'light' ? 'light' : tone === 'brand' ? 'brand' : 'dark'} />
      <span className={`text-[15px] font-semibold tracking-tight ${text}`}>ShopSphere</span>
    </span>
  )
}
