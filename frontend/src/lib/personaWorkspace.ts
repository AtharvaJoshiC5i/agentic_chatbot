/** Role-aware workspace copy, permissions, and starter cards (aligned with questions.md). */

export type WorkspacePersonaId =
  | 'returns_analyst'
  | 'customer_support_agent'
  | 'warehouse_manager'
  | 'returns_supervisor'
  | 'administrator'

export type WorkspaceStarterIcon =
  | 'investigate'
  | 'lookup'
  | 'documents'
  | 'recovery'
  | 'actions'
  | 'approve'
  | 'portfolio'
  | 'customer'
  | 'safety'
  | 'monitoring'
  | 'timeline'

export type WorkspaceStarterCard = {
  id: string
  icon: WorkspaceStarterIcon
  title: string
  subtitle: string
  example_prompt: string
  return_id_hint: string | null
}

export type WorkspacePersona = {
  id: WorkspacePersonaId
  /** Short label for chips and section headers */
  shortName: string
  eyebrow: string
  /** One-line value proposition for marketing / sign-in */
  landingEssence: string
  headline: string
  intro: string
  headerTitle: string
  headerTagline: string
  permissionHints: string[]
  examplesLabel: string
  starters: WorkspaceStarterCard[]
}

const ANALYST: WorkspacePersona = {
  id: 'returns_analyst',
  shortName: 'Returns analyst',
  eyebrow: 'Returns analyst',
  landingEssence: 'Investigate with evidence. Route outcomes for approval.',
  headline: 'Investigate with evidence, then route for approval',
  intro:
    'Build cases from shop data and documents. You can open investigation cases and submit refund requests—execution stays with supervisors.',
  headerTitle: 'Returns analyst',
  headerTagline: 'Investigations, cases, and refund requests',
  permissionHints: ['Investigate & search docs', 'Create cases', 'Request refunds (not execute)'],
  examplesLabel: 'Suggested for analysts',
  starters: [
    {
      id: 'an-r102',
      icon: 'investigate',
      title: 'Investigate R102',
      subtitle: 'Serial mismatch—structured data vs inspection documents',
      example_prompt:
        'Investigate R102 with evidence. Create a case if manual review is required and do not execute a refund.',
      return_id_hint: 'R102',
    },
    {
      id: 'an-r101',
      icon: 'actions',
      title: 'Refund request R101',
      subtitle: 'Eligibility check and submit request for supervisor approval',
      example_prompt:
        'Investigate R101 and submit a refund request if eligible. Do not execute until supervisor approval.',
      return_id_hint: 'R101',
    },
    {
      id: 'an-r110',
      icon: 'documents',
      title: 'Conflicting inspections',
      subtitle: 'Reconcile warehouse narratives on R110',
      example_prompt: 'Investigate R110 and explain any conflicting inspection findings.',
      return_id_hint: 'R110',
    },
    {
      id: 'an-portfolio',
      icon: 'portfolio',
      title: 'Open investigations',
      subtitle: 'Portfolio view of pending and urgent returns',
      example_prompt: 'Which returns are under investigation right now? Highlight anything urgent.',
      return_id_hint: null,
    },
  ],
}

const SUPPORT: WorkspacePersona = {
  id: 'customer_support_agent',
  shortName: 'Customer support',
  eyebrow: 'Customer support',
  landingEssence: 'Customer-ready answers grounded in policy and records.',
  headline: 'Explain outcomes clearly for customer conversations',
  intro:
    'Look up returns, policy, and communications in plain language. Submit refund requests when eligible—never approve or execute payouts yourself.',
  headerTitle: 'Support workspace',
  headerTagline: 'Customer-ready answers and refund requests',
  permissionHints: ['Investigate & explain', 'Search mail & policy', 'Request refunds only'],
  examplesLabel: 'Suggested for support',
  starters: [
    {
      id: 'cs-r101',
      icon: 'customer',
      title: 'Refund status R101',
      subtitle: 'Plain-language summary for a customer callback',
      example_prompt:
        'Explain return R101 in plain language for a customer call and submit a refund request only if eligible.',
      return_id_hint: 'R101',
    },
    {
      id: 'cs-policy',
      icon: 'documents',
      title: 'Return window R103',
      subtitle: 'Policy position and what to tell the customer',
      example_prompt: 'Is R103 inside the return window? What should we tell the customer?',
      return_id_hint: 'R103',
    },
    {
      id: 'cs-r104',
      icon: 'lookup',
      title: 'Delivery damage R104',
      subtitle: 'Complaints and delivery records in one narrative',
      example_prompt: 'Summarize what happened on R104 using complaints and delivery records.',
      return_id_hint: 'R104',
    },
    {
      id: 'cs-r106',
      icon: 'investigate',
      title: 'Duplicate refund R106',
      subtitle: 'Why another refund must be blocked',
      example_prompt: 'Can we refund R106 again? Explain current refund status clearly.',
      return_id_hint: 'R106',
    },
  ],
}

const WAREHOUSE: WorkspacePersona = {
  id: 'warehouse_manager',
  shortName: 'Warehouse',
  eyebrow: 'Warehouse manager',
  landingEssence: 'Receive analyst handoffs and record inspections.',
  headline: 'Receive returns and record inspections',
  intro:
    'When an analyst opens a case, the return appears in your queue. Record receipt, inspect the unit, and confirm whether the claim matches — refund and replacement requests follow the same path.',
  headerTitle: 'Warehouse workspace',
  headerTagline: 'Receipt, inspection, hand back to analyst',
  permissionHints: ['Record receipt & inspection', 'No refunds or supervisor actions'],
  examplesLabel: 'From your queue',
  starters: [
    {
      id: 'wh-queue',
      icon: 'lookup',
      title: 'Open inspection queue',
      subtitle: 'Returns waiting for receipt or inspection',
      example_prompt:
        'List returns in my warehouse handoff queue and what step each needs (receipt vs inspection).',
      return_id_hint: null,
    },
    {
      id: 'wh-r113',
      icon: 'documents',
      title: 'Inspect handoff',
      subtitle: 'Receipt then inspection for an analyst case',
      example_prompt:
        'For return R113: record warehouse receipt if needed, then record inspection with condition, defect verified, and notes. Do not approve refund or replacement.',
      return_id_hint: 'R113',
    },
  ],
}

const SUPERVISOR: WorkspacePersona = {
  id: 'returns_supervisor',
  shortName: 'Supervisor',
  eyebrow: 'Returns supervisor',
  landingEssence: 'Approve analyst refund and replacement requests.',
  headline: 'Approve refund and replacement requests',
  intro:
    'After warehouse inspection, analysts submit requests to you. Approve or reject — they email the customer with the outcome.',
  headerTitle: 'Supervisor workspace',
  headerTagline: 'Refund and replacement approvals',
  permissionHints: ['Approve / reject requests', 'No customer email from you'],
  examplesLabel: 'From your queue',
  starters: [
    {
      id: 'sup-queue',
      icon: 'approve',
      title: 'Pending approvals',
      subtitle: 'What needs a decision today',
      example_prompt:
        'Use list_pending_approvals_tool. Summarize pending refund and replacement requests and inspection status for each return.',
      return_id_hint: null,
    },
    {
      id: 'sup-r101',
      icon: 'actions',
      title: 'Review R101 refund',
      subtitle: 'Workflow + inspection before approve',
      example_prompt:
        'For R101: get_return_workflow_status and get_inspection_results. Recommend approve or reject the pending refund request.',
      return_id_hint: 'R101',
    },
  ],
}

const ADMIN: WorkspacePersona = {
  id: 'administrator',
  shortName: 'Administrator',
  eyebrow: 'Administrator',
  landingEssence: 'Full operational control and demo scenario validation.',
  headline: 'End-to-end demos and break-glass operations',
  intro:
    'Same powers as supervisors plus full API access for pipeline tests. Use starters below to validate investigate → case → refund → recovery flows.',
  headerTitle: 'Admin workspace',
  headerTagline: 'Full pipeline and system oversight',
  permissionHints: ['All supervisor actions', 'Execute gated actions', 'Health & audit views'],
  examplesLabel: 'Demo scenarios',
  starters: [
    {
      id: 'adm-health',
      icon: 'monitoring',
      title: 'System snapshot',
      subtitle: 'Alerts, pending refunds, and unassigned cases',
      example_prompt:
        'Summarize system health: open alerts, pending refunds, and cases without assignee.',
      return_id_hint: null,
    },
    {
      id: 'adm-r102',
      icon: 'investigate',
      title: 'Scenario A — R102',
      subtitle: 'Serial mismatch with case; block premature refund',
      example_prompt:
        'Investigate return R102 and take the necessary actions. Explain findings with evidence, create an investigation case if manual review is required, and do not process a refund yet.',
      return_id_hint: 'R102',
    },
    {
      id: 'adm-r108',
      icon: 'recovery',
      title: 'Scenario C — R108',
      subtitle: 'Best recovery option and repair task',
      example_prompt:
        'Find the best recovery option for R108 and create a repair task if repair-and-resell is recommended.',
      return_id_hint: 'R108',
    },
    {
      id: 'adm-timeline',
      icon: 'timeline',
      title: 'Scenario D — R102 timeline',
      subtitle: 'Chronological journey with source references',
      example_prompt:
        'Show the complete return journey for R102 in chronological order. Include source references for each event.',
      return_id_hint: 'R102',
    },
  ],
}

const PERSONAS: Record<WorkspacePersonaId, WorkspacePersona> = {
  returns_analyst: ANALYST,
  customer_support_agent: SUPPORT,
  warehouse_manager: WAREHOUSE,
  returns_supervisor: SUPERVISOR,
  administrator: ADMIN,
}

export function resolveWorkspacePersonaId(role: string | null): WorkspacePersonaId {
  const r = (role ?? '').toLowerCase()
  if (r.includes('admin')) return 'administrator'
  if (r.includes('supervisor')) return 'returns_supervisor'
  if (r.includes('warehouse')) return 'warehouse_manager'
  if (r.includes('support')) return 'customer_support_agent'
  return 'returns_analyst'
}

/** Personas that land on the focused queue dashboard (minimal nav: queue + agent). */
export function usesFocusedOpsNav(role: string | null): boolean {
  const id = resolveWorkspacePersonaId(role)
  return (
    id === 'returns_analyst' ||
    id === 'warehouse_manager' ||
    id === 'returns_supervisor' ||
    id === 'administrator'
  )
}

export function usesPersonaDashboardHome(role: string | null): boolean {
  return usesFocusedOpsNav(role)
}

/** Nav label “Approvals” and badge polling for supervisor + admin (same backend queue). */
export function showsSupervisorApprovalsNav(role: string | null): boolean {
  const id = resolveWorkspacePersonaId(role)
  return id === 'returns_supervisor' || id === 'administrator'
}

export function workspacePersonaForRole(role: string | null): WorkspacePersona {
  return PERSONAS[resolveWorkspacePersonaId(role)]
}

export function workspacePersonaById(id: WorkspacePersonaId): WorkspacePersona {
  return PERSONAS[id]
}
