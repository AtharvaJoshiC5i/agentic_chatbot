import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatHeader } from '../components/chat/ChatHeader'
import { ChatSidebar } from '../components/chat/ChatSidebar'
import { ContextPanel } from '../components/chat/ContextPanel'
import { MessageList } from '../components/chat/MessageList'
import { WorkspaceEmptyPane } from '../components/chat/WorkspaceEmptyPane'
import { useAuth } from '../context/AuthContext'
import { useLlm } from '../context/LlmContext'
import {
  createConversation,
  createMessage,
  findConversationByReturnId,
  loadConversations,
  normalizeReturnId,
  saveConversations,
  titleFromMessage,
  type Conversation,
  type ToolEvent,
} from '../lib/chats'
import { upsertAgentStep } from '../lib/agentSteps'
import { mergeDocumentSources } from '../lib/documentSources'
import { buildSupportingEvidenceFromResponse } from '../lib/supportingEvidence'
import { notifyWorkspaceDashboardRefresh } from '../lib/workspaceRefresh'
import type { AgentStep } from '../api/types'
export function ChatAppPage() {
  const { username } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const accountKey = useMemo(() => username?.trim() ?? '', [username])
  const { selectedProvider } = useLlm()
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1024)
  const [contextOpen, setContextOpen] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [liveAgentSteps, setLiveAgentSteps] = useState<AgentStep[]>([])
  const [streamingContent, setStreamingContent] = useState<string | null>(null)
  const [contextRefreshKey, setContextRefreshKey] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  const active =
    conversations.find((c) => c.id === activeId) ??
    (conversations[0] ?? null)

  const returnId = active?.returnId ?? null

  const persist = useCallback(
    (next: Conversation[]) => {
      setConversations(next)
      if (accountKey) saveConversations(next, accountKey)
    },
    [accountKey],
  )

  const updateActive = useCallback(
    (updater: (c: Conversation) => Conversation) => {
      if (!activeId) return
      const next = conversations.map((c) => (c.id === activeId ? updater(c) : c))
      persist(next)
    },
    [activeId, conversations, persist],
  )

  const openReturnConversation = useCallback(
    (returnIdRaw: string, draftMessage?: string) => {
      const rid = normalizeReturnId(returnIdRaw)
      if (!rid || !accountKey) return

      const list = conversations.length > 0 ? conversations : loadConversations(accountKey)
      const existing = findConversationByReturnId(list, rid)

      if (existing) {
        setActiveId(existing.id)
        if (draftMessage !== undefined) {
          setDraft(draftMessage)
        }
      } else {
        const c = createConversation(rid)
        c.title = rid
        const next = [c, ...list]
        persist(next)
        setActiveId(c.id)
        setDraft(draftMessage ?? '')
      }

      setContextOpen(true)
      if (window.innerWidth < 1024) setSidebarOpen(false)
    },
    [accountKey, conversations, persist],
  )

  useEffect(() => {
    if (!accountKey) return

    const list = loadConversations(accountKey)
    if (list.length === 0) {
      const c = createConversation()
      saveConversations([c], accountKey)
      setConversations([c])
      setActiveId(c.id)
    } else {
      setConversations(list)
      setActiveId((prev) => (prev && list.some((c) => c.id === prev) ? prev : list[0].id))
    }
    if (!searchParams.get('return')?.trim()) {
      setDraft('')
    }
  }, [accountKey, searchParams])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [active?.messages.length, pending, streamingContent])

  useEffect(() => {
    if (returnId) setContextOpen(true)
  }, [returnId])

  useEffect(() => {
    const raw = searchParams.get('return')?.trim()
    if (!raw || !accountKey) return
    const rid = normalizeReturnId(raw)
    if (!rid) return

    const draftFromNav =
      (location.state as { draftMessage?: string } | null)?.draftMessage?.trim() ?? ''

    openReturnConversation(rid, draftFromNav)
    setSearchParams({}, { replace: true })
    navigate('/workspace', { replace: true, state: {} })
  }, [searchParams, accountKey, location.state, openReturnConversation, navigate, setSearchParams])

  function startNewChat(pinReturn?: string | null) {
    const c = createConversation(pinReturn ?? null)
    if (pinReturn) {
      const rid = normalizeReturnId(pinReturn)
      if (rid) c.title = rid
    }
    const next = [c, ...conversations]
    persist(next)
    setActiveId(c.id)
    setDraft('')
    if (window.innerWidth < 1024) setSidebarOpen(false)
  }

  function selectConversation(id: string) {
    setActiveId(id)
    setDraft('')
    if (window.innerWidth < 1024) setSidebarOpen(false)
  }

  function deleteConversation(id: string) {
    const remaining = conversations.filter((c) => c.id !== id)
    if (remaining.length === 0) {
      const fresh = createConversation()
      persist([fresh])
      setActiveId(fresh.id)
      setDraft('')
      return
    }
    persist(remaining)
    if (activeId === id) {
      setActiveId(remaining[0].id)
      setDraft('')
    }
  }

  async function sendMessage(text: string, pinReturn?: string | null) {
    const trimmed = text.trim()
    if (!trimmed || pending) return

    let conv = active
    if (!conv) {
      conv = createConversation(pinReturn ?? null)
      persist([conv, ...conversations])
      setActiveId(conv.id)
    }

    const effectiveReturn = pinReturn ?? conv.returnId
    const userMsg = createMessage('user', trimmed)
    const historyForApi = conv.messages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    const convAfterUser: Conversation = {
      ...conv,
      returnId: effectiveReturn,
      title: conv.messages.length === 0 ? titleFromMessage(trimmed) : conv.title,
      messages: [...conv.messages, userMsg],
      updatedAt: new Date().toISOString(),
    }

    const nextList = conversations.some((c) => c.id === convAfterUser.id)
      ? conversations.map((c) => (c.id === convAfterUser.id ? convAfterUser : c))
      : [convAfterUser, ...conversations]

    persist(nextList)
    setDraft('')
    setPending(true)
    setLiveAgentSteps([])
    setStreamingContent(null)

    try {
      const res = await api.chatStream(
        {
          message: trimmed,
          return_id: effectiveReturn,
          history: historyForApi.slice(-12),
          llm_provider: selectedProvider as 'groq' | 'gemini' | 'nvidia',
        },
        {
          onStep: (step) => setLiveAgentSteps((prev) => upsertAgentStep(prev, step)),
          onToken: (delta) => {
            setStreamingContent((prev) => (prev ?? '') + delta)
          },
        },
      )

      const toolEvents = res.tool_events as ToolEvent[]
      const assistantMsg = createMessage('assistant', res.final_response, {
        toolEvents,
        agentSteps: res.agent_steps?.length ? res.agent_steps : liveAgentSteps,
        supportingEvidence: buildSupportingEvidenceFromResponse(
          res.supporting_evidence,
          toolEvents,
          res.document_sources,
        ),
        documentSources: mergeDocumentSources(res.document_sources, toolEvents),
        citations: res.citations,
        provider: res.llm_provider,
        model: res.llm_model,
      })

      const inferred = res.inferred_return_id ?? res.return_id
      persist(
        nextList.map((c) =>
          c.id === convAfterUser.id
            ? {
                ...c,
                returnId: c.returnId ?? inferred ?? null,
                messages: [...c.messages, assistantMsg],
                updatedAt: new Date().toISOString(),
              }
            : c,
        ),
      )
    } catch (e) {
      const errMsg = createMessage(
        'assistant',
        e instanceof Error ? e.message : 'Something went wrong. Check that the API is running.',
      )
      persist(
        nextList.map((c) =>
          c.id === convAfterUser.id
            ? {
                ...c,
                messages: [...c.messages, errMsg],
                updatedAt: new Date().toISOString(),
              }
            : c,
        ),
      )
    } finally {
      setPending(false)
      setLiveAgentSteps([])
      setStreamingContent(null)
      setContextRefreshKey((k) => k + 1)
      notifyWorkspaceDashboardRefresh()
    }
  }

  function handleTryExample(message: string, pinReturn?: string | null) {
    if (pinReturn) {
      openReturnConversation(pinReturn)
    }
    void sendMessage(message, pinReturn ?? returnId)
  }

  function setReturnId(id: string | null) {
    updateActive((c) => ({ ...c, returnId: id }))
  }

  const showEmpty = Boolean(active) && active.messages.length === 0 && !pending

  return (
    <div className="workspace-shell flex h-dvh max-h-dvh overflow-hidden font-sans text-stone-900">
      <ChatSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        conversations={conversations}
        activeId={active?.id ?? null}
        onSelect={selectConversation}
        onNewChat={() => startNewChat()}
        onOpenReturn={(id) => openReturnConversation(id, '')}
        onDeleteConversation={deleteConversation}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          onNewChat={() => startNewChat()}
          returnId={returnId}
          contextOpen={contextOpen}
          onToggleContext={() => setContextOpen((v) => !v)}
        />

        <div className="flex min-h-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            <div
              ref={scrollRef}
              className={`workspace-main min-h-0 flex-1 ${
                showEmpty
                  ? 'flex flex-col justify-center overflow-hidden px-4 py-3 sm:px-6'
                  : 'overflow-y-auto overscroll-contain'
              }`}
            >
              {showEmpty ? (
                <WorkspaceEmptyPane onTryExample={handleTryExample} />
              ) : (
                <MessageList
                  messages={active?.messages ?? []}
                  pending={pending}
                  liveAgentSteps={liveAgentSteps}
                  streamingContent={streamingContent}
                />
              )}
            </div>
            <ChatComposer
              value={draft}
              onChange={setDraft}
              disabled={pending}
              returnId={returnId}
              onReturnIdChange={setReturnId}
              onSubmit={() => void sendMessage(draft, returnId)}
            />
          </div>

          {returnId && contextOpen && (
            <>
              <div
                className="fixed inset-0 z-30 bg-stone-900/25 backdrop-blur-[2px] lg:hidden"
                onClick={() => setContextOpen(false)}
                aria-hidden
              />
              <div className="fixed inset-y-0 right-0 z-40 flex w-80 max-w-[90vw] shadow-pop lg:static lg:z-0 lg:max-w-none lg:shadow-none">
                <ContextPanel
                  returnId={returnId}
                  refreshKey={contextRefreshKey}
                  onClose={() => setContextOpen(false)}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
