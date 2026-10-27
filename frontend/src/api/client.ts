import type { CustomerNotificationOut } from './types'
import type {
  AgentCapability,
  AgentStep,
  DataBrowserOverview,
  DocumentBootstrapResult,
  DocumentCatalogStatus,
  DocumentBrowserListResponse,
  DocumentPreview,
  StructuredTableListResponse,
  StructuredTableRowsResponse,
  ActionListResponse,
  ActionOut,
  ChatResponse,
  ChatTurn,
  DashboardSummary,
  WorkspaceDashboardOut,
  InvestigationReportOut,
  LlmProvidersResponse,
  MonitoringSummaryOut,
  RefundableAmountOut,
  RecoveryRecommendationOut,
  RefundOut,
  ReturnDetail,
  ReturnListResponse,
  SystemAlertOut,
  TimelineEventOut,
  TokenResponse,
  InspectionOut,
} from './types'
import { ApiError } from './types'

const TOKEN_KEY = 'shopsphere_access_token'
const ROLE_KEY = 'shopsphere_role'
const USER_KEY = 'shopsphere_username'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredRole(): string | null {
  return localStorage.getItem(ROLE_KEY)
}

function parseSessionTokenPayload(token: string): { sub?: string; exp?: number } | null {
  if (token.startsWith('ss1.')) {
    const parts = token.split('.')
    if (parts.length < 3) return null
    const body = parts[1]
    const pad = '='.repeat((4 - (body.length % 4)) % 4)
    try {
      return JSON.parse(atob(body + pad)) as { sub?: string; exp?: number }
    } catch {
      return null
    }
  }
  try {
    return JSON.parse(atob(token.split('.')[1] ?? '')) as { sub?: string; exp?: number }
  } catch {
    return null
  }
}

export function usernameFromAccessToken(token: string): string | null {
  const payload = parseSessionTokenPayload(token)
  const sub = payload?.sub
  return sub ? String(sub).trim() : null
}

export function getStoredUsername(): string | null {
  const token = getStoredToken()
  const fromToken = token ? usernameFromAccessToken(token) : null
  const stored = localStorage.getItem(USER_KEY)?.trim() ?? null

  if (fromToken && stored && fromToken !== stored) {
    localStorage.setItem(USER_KEY, fromToken)
    return fromToken
  }
  if (stored) return stored
  if (fromToken) {
    localStorage.setItem(USER_KEY, fromToken)
    return fromToken
  }
  return null
}

export function setAuth(token: string, role: string, username: string): void {
  const canonical = username.trim()
  const fromToken = usernameFromAccessToken(token)
  const resolved = fromToken ?? canonical
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(ROLE_KEY, role)
  localStorage.setItem(USER_KEY, resolved)
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(USER_KEY)
}

/** Client-side expiry hint (session `exp` or legacy JWT); does not validate signature. */
export function isAccessTokenExpired(token: string, skewMs = 30_000): boolean {
  if (token.startsWith('ss1.')) {
    const payload = parseSessionTokenPayload(token)
    if (!payload?.exp) return false
    return payload.exp * 1000 < Date.now() + skewMs
  }
  try {
    const payload = JSON.parse(atob(token.split('.')[1] ?? '')) as { exp?: number }
    if (!payload.exp) return false
    return payload.exp * 1000 < Date.now() + skewMs
  } catch {
    return false
  }
}

export function hasValidStoredSession(): boolean {
  const token = getStoredToken()
  return Boolean(token && !isAccessTokenExpired(token))
}

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler | null = null
let unauthorizedNotified = false

export function setOnUnauthorized(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler
  unauthorizedNotified = false
}

export function resetUnauthorizedGuard(): void {
  unauthorizedNotified = false
}

function notifyUnauthorized(): void {
  if (unauthorizedNotified) return
  unauthorizedNotified = true
  onUnauthorized?.()
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, ...init } = options
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth) {
    const token = getStoredToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const res = await fetch(path, { ...init, headers })
  if (res.status === 401 && auth && getStoredToken()) {
    notifyUnauthorized()
  }
  if (!res.ok) {
    let detail: unknown
    try {
      detail = await res.json()
    } catch {
      detail = await res.text()
    }
    const message =
      typeof detail === 'object' && detail !== null && 'detail' in detail
        ? String((detail as { detail: unknown }).detail)
        : res.statusText
    throw new ApiError(res.status, message, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  login(username: string, password: string) {
    return request<TokenResponse>('/api/auth/login', {
      auth: false,
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  dashboardSummary() {
    return request<DashboardSummary>('/api/dashboard/summary')
  },

  workspaceDashboard() {
    return request<WorkspaceDashboardOut>('/api/dashboard/workspace')
  },

  listReturns(params?: { status?: string; limit?: number; offset?: number }) {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    const qs = q.toString()
    return request<ReturnListResponse>(`/api/returns${qs ? `?${qs}` : ''}`)
  },

  getReturn(returnId: string) {
    return request<ReturnDetail>(`/api/returns/${encodeURIComponent(returnId)}`)
  },

  getTimeline(returnId: string, sync = true) {
    const q = sync ? '?sync=true' : '?sync=false'
    return request<TimelineEventOut[]>(
      `/api/returns/${encodeURIComponent(returnId)}/timeline${q}`,
    )
  },

  getInspections(returnId: string) {
    return request<InspectionOut[]>(
      `/api/returns/${encodeURIComponent(returnId)}/inspections`,
    )
  },

  getRefund(returnId: string) {
    return request<RefundOut | null>(
      `/api/returns/${encodeURIComponent(returnId)}/refund`,
    )
  },

  getInvestigation(returnId: string) {
    return request<InvestigationReportOut>(
      `/api/returns/${encodeURIComponent(returnId)}/investigation`,
    )
  },

  getRefundableAmount(returnId: string) {
    return request<RefundableAmountOut>(
      `/api/returns/${encodeURIComponent(returnId)}/refundable`,
    )
  },

  getReturnWorkflow(returnId: string) {
    return request<import('./types').ReturnWorkflowOut>(
      `/api/returns/${encodeURIComponent(returnId)}/workflow`,
    )
  },

  getRecoveryRecommendation(returnId: string) {
    return request<RecoveryRecommendationOut>(
      `/api/recovery/returns/${encodeURIComponent(returnId)}/recommendation`,
    )
  },

  createRecoveryFromRecommendation(returnId: string) {
    return request<unknown>(
      `/api/recovery/returns/${encodeURIComponent(returnId)}/tasks/from-recommendation`,
      { method: 'POST' },
    )
  },

  llmProviders() {
    return request<LlmProvidersResponse>('/api/llm/providers')
  },

  agentCapabilities() {
    return request<AgentCapability[]>('/api/agent/capabilities', { auth: false })
  },

  documentPreview(documentId: number) {
    return request<DocumentPreview>(`/api/documents/${documentId}/preview`)
  },

  dataBrowserOverview() {
    return request<DataBrowserOverview>('/api/data-browser/overview')
  },

  dataBrowserTables() {
    return request<StructuredTableListResponse>('/api/data-browser/tables')
  },

  dataBrowserTableRows(
    tableName: string,
    params?: { limit?: number; offset?: number; col?: string; val?: string },
  ) {
    const q = new URLSearchParams()
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    if (params?.col) q.set('col', params.col)
    if (params?.val != null) q.set('val', params.val)
    const qs = q.toString()
    return request<StructuredTableRowsResponse>(
      `/api/data-browser/tables/${encodeURIComponent(tableName)}/rows${qs ? `?${qs}` : ''}`,
    )
  },

  dataBrowserDocumentsStatus() {
    return request<DocumentCatalogStatus>('/api/data-browser/documents/status')
  },

  dataBrowserDocumentsBootstrap() {
    return request<DocumentBootstrapResult>('/api/data-browser/documents/bootstrap', {
      method: 'POST',
    })
  },

  dataBrowserDocuments(params?: {
    limit?: number
    offset?: number
    document_type?: string
    return_id?: string
    search?: string
    document_id?: number
  }) {
    const q = new URLSearchParams()
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    if (params?.document_type) q.set('document_type', params.document_type)
    if (params?.return_id) q.set('return_id', params.return_id)
    if (params?.search) q.set('search', params.search)
    if (params?.document_id != null) q.set('document_id', String(params.document_id))
    const qs = q.toString()
    return request<DocumentBrowserListResponse>(
      `/api/data-browser/documents${qs ? `?${qs}` : ''}`,
    )
  },

  chat(body: {
    message: string
    conversation_id?: string | null
    return_id?: string | null
    history?: ChatTurn[]
    llm_provider?: 'groq' | 'gemini' | 'nvidia' | null
  }) {
    return request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async chatStream(
    body: {
      message: string
      conversation_id?: string | null
      return_id?: string | null
      history?: ChatTurn[]
      llm_provider?: 'groq' | 'gemini' | 'nvidia' | null
    },
    handlers: {
      onStep: (step: AgentStep) => void
      onToken?: (delta: string) => void
      onStatus?: (data: Record<string, unknown>) => void
    },
  ): Promise<ChatResponse> {
    const token = getStoredToken()
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      if (res.status === 401 && token) notifyUnauthorized()
      let detail = res.statusText
      try {
        const json = (await res.json()) as { detail?: string }
        if (json.detail) detail = json.detail
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail)
    }
    if (!res.body) {
      throw new ApiError(502, 'Empty stream from agent')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let donePayload: ChatResponse | null = null

    const parseBlock = (block: string) => {
      let event = 'message'
      let dataStr = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) dataStr += line.slice(5).trim()
      }
      if (!dataStr) return
      const data = JSON.parse(dataStr) as Record<string, unknown>
      if (event === 'step') handlers.onStep(data as AgentStep)
      if (event === 'token') {
        const delta = (data as { delta?: string }).delta
        if (delta && handlers.onToken) handlers.onToken(delta)
      }
      if (event === 'status' && handlers.onStatus) handlers.onStatus(data)
      if (event === 'error') {
        throw new ApiError(502, String(data.detail ?? 'Agent stream failed'))
      }
      if (event === 'done') donePayload = data as ChatResponse
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        if (part.trim()) parseBlock(part)
      }
    }
    if (buffer.trim()) parseBlock(buffer)

    if (!donePayload) {
      throw new ApiError(502, 'Agent stream ended without a final response')
    }
    return donePayload
  },

  monitoringSummary() {
    return request<MonitoringSummaryOut>('/api/monitoring/summary')
  },

  acknowledgeAlert(alertId: number) {
    return request<SystemAlertOut>(
      `/api/monitoring/alerts/${alertId}/acknowledge`,
      { method: 'POST' },
    )
  },

  runMonitoring() {
    return request<{ open_alerts: number }>('/api/monitoring/run', {
      method: 'POST',
    })
  },

  listActions(returnId: string, limit = 50) {
    return request<ActionListResponse>(
      `/api/actions?return_id=${encodeURIComponent(returnId)}&limit=${limit}`,
    )
  },

  getAction(actionId: number) {
    return request<ActionOut>(`/api/actions/${actionId}`)
  },

  approveAction(actionId: number, approve = true) {
    return request<ActionOut>(`/api/actions/${actionId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approve }),
    })
  },

  executeAction(actionId: number) {
    return request<ActionOut>(`/api/actions/${actionId}/execute`, {
      method: 'POST',
    })
  },

  getApprovals(limit = 100) {
    return request<import('./types').ApprovalsQueueOut>(`/api/approvals?limit=${limit}`)
  },

  approveRefund(refundId: number, approve = true, reason?: string) {
    return request<RefundOut>(`/api/refunds/${refundId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approve, reason }),
    })
  },

  decideReplacement(replacementId: number, approve: boolean, reason?: string) {
    return request<Record<string, unknown>>(`/api/replacements/${replacementId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ approve, reason }),
    })
  },

  recordVerdict(returnId: string, body: { feasible: boolean; recommendation: 'proceed' | 'decline'; notes?: string }) {
    return request<Record<string, unknown>>(`/api/returns/${encodeURIComponent(returnId)}/verdict`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  declineReturn(returnId: string, reason: string) {
    return request<Record<string, unknown>>(`/api/returns/${encodeURIComponent(returnId)}/decline`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  },

  getNotification(notificationId: number) {
    return request<CustomerNotificationOut>(`/api/notifications/${notificationId}`)
  },

  sendNotification(notificationId: number, body: { subject?: string; body?: string }) {
    return request<CustomerNotificationOut>(`/api/notifications/${notificationId}/send`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  listRecoveryTasks(params?: { status?: string; assigned_to?: string; return_id?: string }) {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.assigned_to) q.set('assigned_to', params.assigned_to)
    if (params?.return_id) q.set('return_id', params.return_id)
    const qs = q.toString()
    return request<import('./types').RecoveryTaskOut[]>(
      `/api/recovery/tasks${qs ? `?${qs}` : ''}`,
    )
  },

  patchRecoveryTask(
    taskId: number,
    body: { assigned_to?: string; task_status?: string },
  ) {
    return request<import('./types').RecoveryTaskOut>(`/api/recovery/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  },

  recordInspection(returnId: string, body: Record<string, unknown>) {
    return request<InspectionOut>(`/api/returns/${encodeURIComponent(returnId)}/inspections`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  closeReturn(returnId: string) {
    return request<unknown>(`/api/returns/${encodeURIComponent(returnId)}/close`, {
      method: 'POST',
    })
  },

  resolveCase(caseId: number, resolution_notes?: string) {
    return request<import('./types').CaseOut>(`/api/cases/${caseId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_notes: resolution_notes ?? null }),
    })
  },

  assignCase(caseId: number, assigned_to: string) {
    return request<import('./types').CaseOut>(`/api/cases/${caseId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ assigned_to }),
    })
  },

  listCases(params?: { status?: string }) {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    const qs = q.toString()
    return request<{ items: import('./types').CaseOut[]; total: number }>(
      `/api/cases${qs ? `?${qs}` : ''}`,
    )
  },
}
