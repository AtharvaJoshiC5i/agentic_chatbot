import type { DocumentHit } from '../api/types'
import type { ToolEvent } from './chats'

export function documentSourcesFromToolEvents(events: ToolEvent[]): DocumentHit[] {
  const seen = new Set<string>()
  const out: DocumentHit[] = []
  for (const event of events) {
    for (const hit of event.document_hits ?? []) {
      const key = `${hit.document_id}:${(hit.passage || '').slice(0, 120)}`
      if (seen.has(key)) continue
      seen.add(key)
      out.push(hit)
    }
  }
  return out
}

export function mergeDocumentSources(
  fromApi: DocumentHit[] | undefined,
  toolEvents: ToolEvent[],
): DocumentHit[] {
  const seen = new Set<string>()
  const out: DocumentHit[] = []
  for (const hit of [...(fromApi ?? []), ...documentSourcesFromToolEvents(toolEvents)]) {
    const key = `${hit.document_id}:${(hit.passage || '').slice(0, 120)}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(hit)
  }
  return out
}
