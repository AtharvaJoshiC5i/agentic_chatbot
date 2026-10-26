import type { DocumentHit, SupportingEvidence } from '../api/types'
import type { ToolEvent } from './chats'
import { mergeDocumentSources } from './documentSources'

export function buildSupportingEvidenceFromResponse(
  supporting: SupportingEvidence | undefined,
  toolEvents: ToolEvent[],
  documentSources?: DocumentHit[],
): SupportingEvidence {
  const mergedDocs = mergeDocumentSources(
    documentSources ?? supporting?.documents,
    toolEvents,
  )
  const structured = supporting?.structured ?? []
  if (!structured.length && !mergedDocs.length) {
    return { structured: [], documents: [] }
  }
  const documents =
    mergedDocs.length > 0 ? mergedDocs : (supporting?.documents ?? [])
  return { structured, documents }
}

export function resolveMessageEvidence(
  msg: {
    supportingEvidence?: SupportingEvidence
    documentSources?: DocumentHit[]
    toolEvents?: ToolEvent[]
  },
): SupportingEvidence | undefined {
  if (msg.supportingEvidence) {
    const built = buildSupportingEvidenceFromResponse(
      msg.supportingEvidence,
      msg.toolEvents ?? [],
      msg.documentSources,
    )
    if (built.structured.length || built.documents.length) return built
  }
  if (msg.documentSources?.length || msg.toolEvents?.length) {
    const built = buildSupportingEvidenceFromResponse(undefined, msg.toolEvents ?? [], msg.documentSources)
    if (built.documents.length) return built
  }
  return undefined
}
