/** Shared Tailwind class recipes — restrained, ops-console polish. */

export const container = 'mx-auto w-full max-w-6xl px-5 sm:px-8'

export const eyebrow = 'text-xs font-medium text-stone-500'

const buttonBase =
  'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600 disabled:pointer-events-none disabled:opacity-50'

const buttonVariants = {
  primary: 'bg-accent-600 text-white hover:bg-accent-700',
  secondary: 'border border-stone-200 bg-white text-stone-800 hover:bg-stone-50',
  ghost: 'text-stone-600 hover:bg-stone-100 hover:text-stone-900',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  inverse: 'bg-white text-stone-900 hover:bg-stone-100',
} as const

const buttonSizes = {
  sm: 'h-9 px-3 text-[13px]',
  md: 'h-10 px-4 text-sm',
  lg: 'h-11 px-5 text-sm',
} as const

export function button(
  variant: keyof typeof buttonVariants = 'primary',
  size: keyof typeof buttonSizes = 'md',
): string {
  return `${buttonBase} ${buttonVariants[variant]} ${buttonSizes[size]}`
}

export const iconButton =
  'inline-flex size-9 min-h-9 min-w-9 shrink-0 items-center justify-center rounded-md text-stone-600 transition-colors hover:bg-stone-100 hover:text-stone-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600 disabled:opacity-50'

export const workspaceIconButton =
  'inline-flex size-8 min-h-8 min-w-8 shrink-0 items-center justify-center rounded-md text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600 disabled:opacity-50'

export const fieldLabel = 'mb-1.5 block text-sm font-medium text-stone-700'

export const fieldInput =
  'block h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-stone-900 placeholder:text-stone-400 transition-colors focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-600/20 disabled:bg-stone-50 disabled:text-stone-500'

export const sidebarSectionLabel = 'px-2 text-xs font-medium text-stone-500'

export const sidebarSearchInput =
  'h-9 w-full rounded-md border border-stone-200 bg-white pl-8 pr-2.5 text-[13px] text-stone-900 placeholder:text-stone-400 focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-600/20'

export const panelTitle = 'text-xs font-medium text-stone-500'

export function segmentedTab(active: boolean): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    active ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'
  }`
}

export function navPill(active: boolean): string {
  return `inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    active
      ? 'bg-stone-100 text-stone-900'
      : 'text-stone-600 hover:bg-stone-50 hover:text-stone-900'
  }`
}
