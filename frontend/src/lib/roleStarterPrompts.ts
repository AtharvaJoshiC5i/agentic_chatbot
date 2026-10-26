import type { StarterPrompt } from './starterPrompts'
import { workspacePersonaForRole } from './personaWorkspace'

export function promptsForRole(role: string | null): StarterPrompt[] {
  const persona = workspacePersonaForRole(role)
  return persona.starters.map((s) => ({
    id: s.id,
    label: s.title,
    message: s.example_prompt,
    returnId: s.return_id_hint ?? undefined,
  }))
}
