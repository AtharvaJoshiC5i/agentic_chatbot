import type { ChatVisual } from '../lib/visuals'
export type TokenResponse = {
  access_token: string
  token_type: string
  role: string
  username: string
}

export type ReturnSummary = {
  return_id: string
  order_item_id: number
  return_reason: string
  return_status: string
  request_date: string
  received_date: string | null
  requested_resolution: string
}

export type ReturnListResponse = {
  items: ReturnSummary[]
  total: number
  limit: number
  offset: number
}

export type ProductSummary = {
  product_id: string
  product_name: string
  category: string
  brand: string
  original_price_paise: number
}

export type OrderItemSummary = {
  order_item_id: number
  product_id: string
  quantity: number
  unit_price_paise: number
  purchased_serial_number: string | null
}

export type OrderDetail = {
  order_id: string
  customer_id: string
  order_date: string
  total_amount_paise: number
  order_status: string
  items: OrderItemSummary[]
}

export type DeliverySummary = {
  delivery_id: string
  dispatch_date: string | null
  delivery_date: string | null
  delivery_status: string
  delivery_issue: string | null
}

export type ReturnDetail = ReturnSummary & {
  customer_description: string | null
  order: OrderDetail | null
  product: ProductSummary | null
  delivery: DeliverySummary | null
}

export type InspectionOut = {
  inspection_id: number
  return_id: string
  inspection_date: string
  returned_serial_number: string | null
  product_condition: string
  accessories_complete: boolean
  defect_verified: boolean
  inspection_result: string
  inspector_notes: string | null
}

export type RefundOut = {
  refund_id: number
  return_id: string
  refund_amount_paise: number
  refund_status: string
  approval_status: string
  processed_date: string | null
  idempotency_key: string
}

export type TimelineEventOut = {
  event_id: number
  return_id: string
  event_type: string
  event_timestamp: string
  description: string
  source_type: string
  source_id: string
}

export type RecoveryTaskOut = {
  recovery_task_id: number
  return_id: string
  recovery_method: string
  assigned_to: string | null
  task_status: string
  created_at: string
  completed_at: string | null
}

export type ApprovalsQueueOut = {
  refunds: {
    refund_id: number
    return_id: string
    amount_paise: number
    kind: string
  }[]
  actions: {
    action_id: number
    return_id: string
    action_type: string
    requested_by: string
    age_minutes: number | null
    kind: string
  }[]
}

export type CaseOut = {
  case_id: number
  return_id: string
  issue_type: string
  priority: string
  assigned_to: string | null
  case_status: string
  created_at: string
  due_date: string | null
  resolution_notes: string | null
}

export type DashboardSummary = {
  total_returns: number
  pending_investigations: number
  refunds_awaiting_approval: number
  actions_awaiting_approval?: number
  open_recovery_tasks: number
  estimated_recovery_value_paise: number
  completed_recovery_tasks: number
  returns_investigating: number
  overdue_investigation_cases: number
  open_system_alerts: number
  generated_at: string
}

export type WorkspaceQueueItem = {
  kind: string
  title: string
  subtitle?: string | null
  return_id?: string | null
  case_id?: number | null
  recovery_task_id?: number | null
  action_id?: number | null
  refund_id?: number | null
  alert_id?: number | null
  severity?: string | null
  status?: string | null
  priority?: string | null
  due_date?: string | null
  amount_paise?: number | null
  assigned_to?: string | null
  overdue?: boolean | null
  workflow_stage?: string | null
  next_action?: string | null
  requested_resolution?: string | null
  approval_kind?: string | null
  requested_by?: string | null
  action_type?: string | null
  status_summary?: string | null
  inspection_count?: number | null
  refund_status?: string | null
  approval_status?: string | null
  your_move?: boolean | null
  replacement_id?: number | null
  notification_id?: number | null
  warehouse_verdict?: string | { recommendation?: string; notes?: string | null; resolution_type?: string } | null
  warehouse_notes?: string | null
  workflow_timeline?: Array<{
    event_id: number
    event_type: string
    event_timestamp: string
    description: string
    source_type: string
  }>
}

export type CustomerNotificationOut = {
  notification_id: number
  return_id: string
  kind: string
  to_email: string
  subject: string
  body: string
  status: 'draft' | 'sent'
  created_by: string
  created_at: string | null
  sent_by: string | null
  sent_at: string | null
}

export type WorkspaceDashboardSection = {
  key: string
  title: string
  items: WorkspaceQueueItem[]
}

export type WorkspaceDashboardOut = {
  persona: 'returns_analyst' | 'warehouse_manager' | 'returns_supervisor'
  generated_at: string
  kpis: Record<string, number>
  sections: WorkspaceDashboardSection[]
}

export type InvestigationCheckOut = {
  check_id: string
  title: string
  status: string
  summary: string
  details: Record<string, unknown>
}

export type PolicyEvaluationOut = {
  product_category: string
  return_window_days: number
  days_after_delivery: number | null
  within_return_window: boolean | null
  warranty_months: number
  order_age_days: number | null
  within_warranty_period: boolean | null
  delivery_date: string | null
  return_request_date: string | null
}

export type InvestigationReportOut = {
  return_id: string
  scenario_slug: string | null
  checks: InvestigationCheckOut[]
  f2_signal: string
  f3_policy: PolicyEvaluationOut
  f4_outcome: string
  recommended_actions: string[]
  generated_at: string
}

export type RankedRecoveryOptionOut = {
  option_id: number
  recovery_method: string
  expected_net_recovery_paise: number
  feasibility_status: string
  expected_revenue_paise: number
  total_cost_paise: number
  rank: number
  eligible: boolean
  exclusion_reason: string | null
}

export type RecoveryRecommendationOut = {
  return_id: string
  unsafe_product: boolean
  recommended_option_id: number | null
  recommended_method: string | null
  rationale: string
  requires_approval: boolean
  ranked_options: RankedRecoveryOptionOut[]
}

export type LlmProviderId = 'groq' | 'gemini' | 'nvidia'

export type LlmProviderOption = {
  id: LlmProviderId
  label: string
  configured: boolean
  model: string
  max_rpm: number
  is_default: boolean
}

export type LlmProvidersResponse = {
  default_provider: string
  providers: LlmProviderOption[]
}

export type ChatTurn = { role: string; content: string }

export type AgentStep = {
  index: number
  kind: string
  title: string
  status: string
  detail?: string | null
  tool?: string | null
  input?: string | null
  output?: string | null
}

export type AgentCapability = {
  id: string
  title: string
  description: string
  example_prompt: string
  tools: string[]
  return_id_hint: string | null
}

export type StructuredEvidence = {
  evidence_id: string
  source_tool: string
  table_name: string
  title: string
  columns: string[]
  rows: Record<string, string>[]
  record?: Record<string, unknown> | null
}

export type SupportingEvidence = {
  structured: StructuredEvidence[]
  documents: DocumentHit[]
}

export type DocumentHit = {
  document_id: number
  filename: string
  file_path: string
  page_or_section?: string | null
  passage: string
  relevance_score?: number | null
  file_kind: string
}

export type DocumentPreviewSegment = {
  page: number | null
  section: string | null
  text: string
}

export type DataBrowserOverview = {
  database_url: string
  database_file: string | null
  database_file_exists: boolean
  structured_table_count: number
  structured_row_count: number
  document_count: number
  document_types: string[]
}

export type StructuredTableSummary = {
  name: string
  label: string
  row_count: number
  column_count: number
}

export type StructuredTableListResponse = {
  tables: StructuredTableSummary[]
}

export type StructuredTableRowsResponse = {
  table_name: string
  label: string
  columns: string[]
  rows: Record<string, string>[]
  total: number
  limit: number
  offset: number
}

export type DocumentBrowserItem = {
  document_id: number
  filename: string
  document_type: string
  return_id: string | null
  product_id: string | null
  file_path: string
  file_kind: string
  created_at: string
  policy_version: string | null
  effective_date: string | null
}

export type DocumentBrowserListResponse = {
  items: DocumentBrowserItem[]
  total: number
  limit: number
  offset: number
  document_types: string[]
}

export type DocumentPreview = {
  document_id: number
  filename: string
  file_path: string
  file_kind: string
  mime_type: string
  segments: DocumentPreviewSegment[]
  full_text: string
}

export type ChatResponse = {
  conversation_id: string | null
  return_id: string | null
  inferred_return_id?: string | null
  final_response: string
  tool_events: Record<string, unknown>[]
  agent_steps?: AgentStep[]
  visuals?: ChatVisual[]
  supporting_evidence?: SupportingEvidence
  document_sources?: DocumentHit[]
  llm_provider: string
  llm_model: string
}

export type SystemAlertOut = {
  alert_id: number
  related_entity: string
  related_id: string
  alert_type: string
  severity: string
  status: string
  created_at: string
}

export type MonitoringSummaryOut = {
  open_alerts: number
  alerts: SystemAlertOut[]
}

export type RefundableAmountOut = {
  line_total_paise: number
  already_refunded_paise: number
  remaining_refundable_paise: number
}

export type ActionOut = {
  action_id: number
  return_id: string | null
  action_type: string
  requested_by: string
  approval_required: boolean
  approval_status: string
  execution_status: string
  created_at: string
  executed_at: string | null
  idempotency_key: string
  payload: Record<string, unknown>
}

export type ActionListResponse = {
  items: ActionOut[]
  total: number
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}
