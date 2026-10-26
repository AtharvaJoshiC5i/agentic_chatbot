import type { AgentCapability } from '../api/types'

/** Mirrors backend `app.agents.capabilities` — used when the API is unreachable. */
export const DEFAULT_AGENT_CAPABILITIES: AgentCapability[] = [
  {
    id: 'investigate',
    title: 'Investigate a return',
    description: 'Full eligibility check with policy and recommended next steps.',
    example_prompt:
      'Investigate return R102 and tell me in plain language if we should refund, escalate, or verify further.',
    tools: ['run_return_investigation'],
    return_id_hint: 'R102',
  },
  {
    id: 'lookup',
    title: 'Look up shop records',
    description: 'Return, order, delivery, inspection, and refund status.',
    example_prompt: 'Pull full details for return R106 including refund status.',
    tools: ['get_return_details', 'get_order_details', 'get_inspection_results', 'get_refund_status'],
    return_id_hint: 'R106',
  },
  {
    id: 'documents',
    title: 'Search policies & communications',
    description: 'Complaints, emails, warranty, and return policy documents.',
    example_prompt: 'Search complaints about serial verification for R102.',
    tools: ['search_customer_complaints', 'search_return_policy', 'resolve_applicable_policy'],
    return_id_hint: 'R102',
  },
  {
    id: 'recovery',
    title: 'Recommend product recovery',
    description: 'Compare repair, refurb, and disposal by net value.',
    example_prompt: 'What recovery do you recommend for R108?',
    tools: ['get_recovery_options', 'get_recovery_recommendation'],
    return_id_hint: 'R108',
  },
  {
    id: 'actions',
    title: 'Submit operational actions',
    description: 'Open cases, refund requests, or recovery tasks (approval when required).',
    example_prompt: 'Open an investigation case for R103 if outside policy.',
    tools: ['submit_create_investigation_case', 'submit_refund_request', 'submit_repair_recovery_task'],
    return_id_hint: 'R103',
  },
]
