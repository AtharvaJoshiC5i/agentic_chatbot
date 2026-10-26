/** Normalize whitespace for fuzzy passage matching inside document preview. */
export function normalizeForMatch(value: string): string {
  return value.replace(/\s+/g, ' ').trim().toLowerCase()
}

export type TextPart = { text: string; highlight: boolean }

/**
 * Split `text` into parts, marking the first occurrence of `passage` (or a prefix) as highlighted.
 */
export function splitTextWithHighlight(text: string, passage: string): TextPart[] {
  const trimmedPassage = passage.trim()
  if (!trimmedPassage) {
    return [{ text, highlight: false }]
  }

  const candidates = [
    trimmedPassage,
    trimmedPassage.slice(0, Math.min(120, trimmedPassage.length)),
    trimmedPassage.slice(0, Math.min(60, trimmedPassage.length)),
  ].filter((c, i, arr) => c.length >= 12 && arr.indexOf(c) === i)

  for (const candidate of candidates) {
    const idx = text.indexOf(candidate)
    if (idx >= 0) {
      const parts: TextPart[] = []
      if (idx > 0) parts.push({ text: text.slice(0, idx), highlight: false })
      parts.push({ text: text.slice(idx, idx + candidate.length), highlight: true })
      const rest = text.slice(idx + candidate.length)
      if (rest) parts.push({ text: rest, highlight: false })
      return parts
    }
  }

  const normText = normalizeForMatch(text)
  const normPassage = normalizeForMatch(trimmedPassage)
  const normIdx = normText.indexOf(normPassage.slice(0, Math.min(80, normPassage.length)))
  if (normIdx >= 0) {
    const ratio = text.length / Math.max(normText.length, 1)
    const approxStart = Math.floor(normIdx * ratio)
    const approxLen = Math.min(trimmedPassage.length, text.length - approxStart)
    if (approxLen > 8) {
      return [
        { text: text.slice(0, approxStart), highlight: false },
        { text: text.slice(approxStart, approxStart + approxLen), highlight: true },
        { text: text.slice(approxStart + approxLen), highlight: false },
      ]
    }
  }

  return [{ text, highlight: false }]
}
