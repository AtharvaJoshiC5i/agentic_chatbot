import { createContext, useCallback, useContext, useMemo, useState } from 'react'

type Toast = { id: number; message: string; tone: 'error' | 'info' }

type ToastContextValue = {
  showToast: (message: string, tone?: 'error' | 'info') => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, tone: 'error' | 'info' = 'error') => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, message, tone }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 6000)
  }, [])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-lg border px-4 py-3 text-sm shadow-lg ${
              t.tone === 'error'
                ? 'border-red-200 bg-red-50 text-red-900'
                : 'border-stone-200 bg-white text-stone-800'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    return { showToast: () => {} }
  }
  return ctx
}
