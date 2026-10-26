import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import type { LlmProviderOption } from '../api/types'
import { useAuth } from './AuthContext'

type LlmState = {
  providers: LlmProviderOption[]
  defaultProvider: string
  selectedProvider: string
  setSelectedProvider: (id: string) => void
  loading: boolean
  refresh: () => Promise<void>
}

const STORAGE_KEY = 'shopsphere_llm_provider'

const LlmContext = createContext<LlmState | null>(null)

export function LlmProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [providers, setProviders] = useState<LlmProviderOption[]>([])
  const [defaultProvider, setDefaultProvider] = useState('groq')
  const [selectedProvider, setSelectedProviderState] = useState(() =>
    localStorage.getItem(STORAGE_KEY) ?? '',
  )
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.llmProviders()
      setProviders(res.providers)
      setDefaultProvider(res.default_provider)
      const stored = localStorage.getItem(STORAGE_KEY)
      const configured = res.providers.filter((p) => p.configured)
      const pick =
        stored && configured.some((p) => p.id === stored)
          ? stored
          : res.default_provider
      setSelectedProviderState(pick)
      localStorage.setItem(STORAGE_KEY, pick)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) void refresh()
  }, [isAuthenticated, refresh])

  const setSelectedProvider = useCallback((id: string) => {
    setSelectedProviderState(id)
    localStorage.setItem(STORAGE_KEY, id)
  }, [])

  const value = useMemo(
    () => ({
      providers,
      defaultProvider,
      selectedProvider: selectedProvider || defaultProvider,
      setSelectedProvider,
      loading,
      refresh,
    }),
    [
      providers,
      defaultProvider,
      selectedProvider,
      setSelectedProvider,
      loading,
      refresh,
    ],
  )

  return <LlmContext.Provider value={value}>{children}</LlmContext.Provider>
}

export function useLlm(): LlmState {
  const ctx = useContext(LlmContext)
  if (!ctx) throw new Error('useLlm must be used within LlmProvider')
  return ctx
}
