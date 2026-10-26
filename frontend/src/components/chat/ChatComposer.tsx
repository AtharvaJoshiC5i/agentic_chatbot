import { ArrowUp, ChevronDown, Tag, X } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useLlm } from '../../context/LlmContext'

function ComposerModelMenu({ disabled }: { disabled: boolean }) {
  const { providers, selectedProvider, setSelectedProvider, loading } = useLlm()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const current = providers.find((p) => p.id === selectedProvider)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (loading && providers.length === 0) {
    return (
      <div
        className="h-7 w-[5.5rem] animate-pulse rounded-md bg-stone-100 motion-reduce:animate-none"
        aria-hidden
      />
    )
  }

  if (providers.length === 0) return null

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Choose model"
        className="inline-flex h-7 max-w-[9.5rem] items-center gap-0.5 rounded-md border border-transparent px-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-stone-200 hover:bg-stone-50 disabled:opacity-50"
      >
        <span className="truncate">{current?.label ?? 'Model'}</span>
        <ChevronDown
          className={`size-3.5 shrink-0 text-stone-400 transition-transform ${open ? 'rotate-180' : ''}`}
          strokeWidth={2}
          aria-hidden
        />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Models"
          className="absolute bottom-full left-0 z-50 mb-1.5 w-[min(100vw-2rem,13rem)] overflow-hidden rounded-lg border border-stone-200 bg-white py-1 shadow-elevated"
        >
          {providers.map((p) => {
            const selected = p.id === selectedProvider
            const itemDisabled = disabled || !p.configured
            return (
              <li key={p.id} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  disabled={itemDisabled}
                  title={p.configured ? p.model : `${p.label} is not configured`}
                  onClick={() => {
                    setSelectedProvider(p.id)
                    setOpen(false)
                  }}
                  className={`flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-45 ${
                    selected ? 'bg-stone-50' : ''
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-stone-900">{p.label}</span>
                    {selected && (
                      <span className="text-[10px] font-medium text-accent-700">Active</span>
                    )}
                  </span>
                  <span className="truncate text-[10px] leading-tight text-stone-500">
                    {p.configured ? p.model : 'Not configured'}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  disabled,
  returnId,
  onReturnIdChange,
}: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  disabled: boolean
  returnId: string | null
  onReturnIdChange: (id: string | null) => void
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [pinOpen, setPinOpen] = useState(false)
  const [pinDraft, setPinDraft] = useState('')

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 112)}px`
  }, [value])

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) onSubmit()
    }
  }

  function onFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!disabled && value.trim()) onSubmit()
  }

  function applyPin() {
    const v = pinDraft.trim().toUpperCase()
    if (v) onReturnIdChange(v)
    setPinDraft('')
    setPinOpen(false)
  }

  const canSend = !disabled && value.trim().length > 0

  return (
    <div className="chat-composer-dock shrink-0 px-4 pb-3 pt-1.5 sm:px-6">
      <form onSubmit={onFormSubmit} className="mx-auto w-full max-w-2xl lg:max-w-[40rem]">
        <div className="chat-composer-shell px-3 py-2 sm:px-3.5 sm:py-2.5">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Message ShopSphere…"
            className="block max-h-28 min-h-[1.25rem] w-full resize-none bg-transparent text-sm leading-snug text-stone-900 placeholder:text-stone-400 focus:outline-none disabled:text-stone-500"
            aria-label="Message"
          />

          <div className="mt-1.5 flex items-center justify-between gap-2">
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-0.5">
              {pinOpen ? (
                <div className="flex flex-wrap items-center gap-1.5">
                  <input
                    type="text"
                    value={pinDraft}
                    onChange={(e) => setPinDraft(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        applyPin()
                      }
                      if (e.key === 'Escape') setPinOpen(false)
                    }}
                    placeholder="R102"
                    aria-label="Return ID"
                    autoFocus
                    className="h-7 w-[4.25rem] rounded-md border border-stone-200 bg-stone-50 px-2 font-mono text-[11px] text-stone-900 focus:border-stone-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-stone-900/10"
                  />
                  <button
                    type="button"
                    onClick={applyPin}
                    className="h-7 rounded-md bg-stone-900 px-2 text-[11px] font-medium text-white hover:bg-stone-800"
                  >
                    Add
                  </button>
                  <button
                    type="button"
                    onClick={() => setPinOpen(false)}
                    className="h-7 px-1.5 text-[11px] font-medium text-stone-500 hover:text-stone-800"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setPinOpen(true)}
                    className="inline-flex size-7 items-center justify-center rounded-md text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
                    aria-label="Link a return ID"
                  >
                    <Tag className="size-4" strokeWidth={1.75} aria-hidden />
                  </button>
                  {returnId && (
                    <span
                      className="inline-flex h-7 max-w-[6.5rem] items-center gap-0.5 rounded-md bg-stone-100 pl-2 pr-0.5 text-[11px] font-medium text-stone-700"
                    >
                      <span className="truncate font-mono">{returnId}</span>
                      <button
                        type="button"
                        onClick={() => onReturnIdChange(null)}
                        aria-label="Remove return context"
                        className="inline-flex size-5 shrink-0 items-center justify-center rounded text-stone-400 hover:bg-stone-200/80 hover:text-stone-700"
                      >
                        <X className="size-3" strokeWidth={2} aria-hidden />
                      </button>
                    </span>
                  )}
                  <span className="mx-0.5 hidden h-4 w-px bg-stone-200 sm:inline" aria-hidden />
                  <ComposerModelMenu disabled={disabled} />
                </>
              )}
            </div>

            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send message"
              title="Enter to send"
              className={`inline-flex size-8 shrink-0 items-center justify-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600 ${
                canSend
                  ? 'bg-stone-900 text-white hover:bg-stone-800'
                  : 'cursor-not-allowed bg-stone-200 text-stone-400'
              }`}
            >
              <ArrowUp className="size-4" strokeWidth={2.25} aria-hidden />
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
