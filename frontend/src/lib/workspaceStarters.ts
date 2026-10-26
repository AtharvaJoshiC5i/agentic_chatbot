/** Default capability card copy; empty-state starters live in personaWorkspace.ts */

import { workspacePersonaForRole } from './personaWorkspace'

export type WorkspaceStarter = {
  id: string
  title: string
  subtitle: string
  example_prompt: string
  return_id_hint: string | null
}

/** Display copy for capability cards (AgentGuide + API merge). */
export const WORKSPACE_CARD_COPY: Record<
  string,
  { blurb: string; exampleLabel: string }
> = {
  investigate: {
    blurb: 'Eligibility, policy window, and recommended next step',
    exampleLabel: 'Investigate return R102 in plain language',
  },
  lookup: {
    blurb: 'Order, delivery, inspection, and refund status',
    exampleLabel: 'Full details for return R106',
  },
  documents: {
    blurb: 'Complaints, emails, and applicable return policy',
    exampleLabel: 'Serial verification complaints for R102',
  },
  recovery: {
    blurb: 'Repair, refurbish, or dispose by net value',
    exampleLabel: 'Recovery recommendation for R108',
  },
  actions: {
    blurb: 'Cases, refund requests, and recovery tasks when approval is required',
    exampleLabel: 'Open a case for R103 if outside policy',
  },
}

/** Generic fallback when role is unknown (returns analyst starters). */
export const WORKSPACE_STARTERS: WorkspaceStarter[] = workspacePersonaForRole(
  'returns_analyst',
).starters.map((s) => ({
  id: s.id,
  title: s.title,
  subtitle: s.subtitle,
  example_prompt: s.example_prompt,
  return_id_hint: s.return_id_hint,
}))
