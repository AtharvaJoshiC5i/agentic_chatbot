export function Avatar({ label, size = 'md' }: { label: string; size?: 'sm' | 'md' }) {
  const initials = label
    .split(/[\s_@]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
  const dim = size === 'sm' ? 'size-8 text-xs' : 'size-9 text-sm'
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-zinc-200 font-medium text-zinc-700 ${dim}`}
      aria-hidden
    >
      {initials || '?'}
    </span>
  )
}
