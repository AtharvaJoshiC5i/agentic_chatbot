import type { AgentStep, Citation, DocumentHit, SupportingEvidence } from '../api/types'
import { chatStorageKey, importLegacyConversationsIfNeeded, normalizeChatAccount } from './chatAccount'

export type ToolEvent = {
  tool?: string
  args?: Record<string, unknown>
  result_preview?: string
  document_hits?: DocumentHit[]
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolEvents?: ToolEvent[]
  agentSteps?: AgentStep[]
  documentSources?: DocumentHit[]
  supportingEvidence?: SupportingEvidence
  citations?: Citation[]
  provider?: string
  model?: string
  createdAt: string
}

export type Conversation = {
  id: string
  title: string
  returnId: string | null
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

function newId(): string {
  return crypto.randomUUID()
}

function resolveUsername(username: string | null | undefined): string | null {
  const u = normalizeChatAccount(username ?? '')
  return u || null
}

export function loadConversations(username: string | null | undefined): Conversation[] {
  const account = resolveUsername(username)
  if (!account) return []

  importLegacyConversationsIfNeeded(account)

  try {
    const raw = localStorage.getItem(chatStorageKey(account))
    if (!raw) return []
    const parsed = JSON.parse(raw) as Conversation[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveConversations(
  conversations: Conversation[],
  username: string | null | undefined,
): void {
  const account = resolveUsername(username)
  if (!account) return
  localStorage.setItem(chatStorageKey(account), JSON.stringify(conversations))
}

export function createConversation(returnId: string | null = null): Conversation {
  const now = new Date().toISOString()
  return {
    id: newId(),
    title: 'New conversation',
    returnId,
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

export function createMessage(
  role: ChatMessage['role'],
  content: string,
  extra?: Partial<
    Pick<
      ChatMessage,
      'toolEvents' | 'agentSteps' | 'documentSources' | 'supportingEvidence' | 'citations' | 'provider' | 'model'
    >
  >,
): ChatMessage {
  return {
    id: newId(),
    role,
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  }
}

export function titleFromMessage(text: string): string {
  const t = text.trim().replace(/\s+/g, ' ')
  if (t.length <= 48) return t || 'New conversation'
  return `${t.slice(0, 45)}…`
}

export function normalizeReturnId(id: string): string | null {
  const rid = id.trim().toUpperCase()
  return /^R\d+$/.test(rid) ? rid : null
}

export function findConversationByReturnId(
  conversations: Conversation[],
  returnId: string,
): Conversation | undefined {
  const rid = normalizeReturnId(returnId)
  if (!rid) return undefined
  return conversations.find((c) => c.returnId?.toUpperCase() === rid)
}
