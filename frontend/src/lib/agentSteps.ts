import type { AgentStep } from '../api/types'

export function upsertAgentStep(steps: AgentStep[], row: AgentStep): AgentStep[] {
  const next = [...steps]
  const idx = next.findIndex((s) => s.index === row.index)
  if (idx >= 0) {
    next[idx] = row
  } else {
    next.push(row)
  }
  return next.sort((a, b) => a.index - b.index)
}
