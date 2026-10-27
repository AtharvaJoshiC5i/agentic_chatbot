/** Remove auto-appended reference footers from assistant markdown (sources live in the Sources panel). */

export function stripAssistantReferencesFooter(content: string): string {
  let text = content
  const refBlock = text.search(/\n---\s*\n+\*\*References\*\*/i)
  if (refBlock >= 0) {
    text = text.slice(0, refBlock)
  }
  text = text.replace(/\n\n\*\*Sources\*\*[\s\S]*$/i, '')
  return text.trimEnd()
}
