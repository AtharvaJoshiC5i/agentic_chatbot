import type { WorkspacePersonaId } from './personaWorkspace'

export type DemoAccount = {
  personaId: WorkspacePersonaId
  username: string
  password: string
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { personaId: 'returns_analyst', username: 'returns_analyst', password: 'ShopSphere@Analyst1' },
  { personaId: 'warehouse_manager', username: 'warehouse_mgr', password: 'ShopSphere@Warehouse1' },
  {
    personaId: 'returns_supervisor',
    username: 'returns_supervisor',
    password: 'ShopSphere@Super1',
  },
]

export const LANDING_ROLE_ORDER: WorkspacePersonaId[] = [
  'returns_analyst',
  'warehouse_manager',
  'returns_supervisor',
]

export function demoAccountForPersona(personaId: WorkspacePersonaId): DemoAccount {
  const found = DEMO_ACCOUNTS.find((a) => a.personaId === personaId)
  return found ?? DEMO_ACCOUNTS[0]
}

export function parsePersonaIdParam(raw: string | null): WorkspacePersonaId | null {
  if (!raw) return null
  const id = raw.trim() as WorkspacePersonaId
  return DEMO_ACCOUNTS.some((a) => a.personaId === id) ? id : null
}
