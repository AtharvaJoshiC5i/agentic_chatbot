export type StarterPrompt = {
  id: string
  label: string
  message: string
  returnId?: string
}

export const STARTER_PROMPTS: StarterPrompt[] = [
  {
    id: 'inv-r102',
    label: 'Investigate R102',
    returnId: 'R102',
    message:
      'Run a full investigation on return R102. Explain F2 signals, policy (F3), and your recommended outcome (F4).',
  },
  {
    id: 'recovery-r108',
    label: 'Recovery for R108',
    returnId: 'R108',
    message:
      'What recovery options and net value do we have for R108? Recommend repair vs refurbish and whether approval is needed.',
  },
  {
    id: 'refund-r106',
    label: 'Refund risk R106',
    returnId: 'R106',
    message:
      'Check refund and duplicate-payment risk for R106. Summarize timeline events and what action you recommend.',
  },
  {
    id: 'policy-r103',
    label: 'Policy R103',
    returnId: 'R103',
    message:
      'Is R103 inside the return window? Cite applicable policy and what we should tell the customer.',
  },
  {
    id: 'safety-r115',
    label: 'Safety R115',
    returnId: 'R115',
    message:
      'Assess product safety for R115 and whether recovery or resale is allowed. Use investigation and recovery tools.',
  },
  {
    id: 'docs',
    label: 'Search documents',
    message:
      'Search support communications about serial number verification and summarize what agents should verify before approving a refund.',
  },
]
