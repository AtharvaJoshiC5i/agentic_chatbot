/** Normalize whitespace for fuzzy passage matching inside document preview. */
export function normalizeForMatch(value: string): string {
  return value.replace(/\s+/g, ' ').trim().toLowerCase()
}

export type TextPart = { text: string; highlight: boolean }

export type PassageRange = { start: number; end: number }

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Locate one contiguous span in `text` that best matches the cited `passage` (flexible whitespace).
 */
export function findPassageRange(text: string, passage: string): PassageRange | null {
  const trimmedPassage = passage.trim()
  if (!trimmedPassage || !text) return null

  const direct = text.indexOf(trimmedPassage)
  if (direct >= 0) {
    return { start: direct, end: direct + trimmedPassage.length }
  }

  const flexPattern = escapeRegExp(trimmedPassage).replace(/\s+/g, '\\s+')
  const flex = new RegExp(flexPattern, 'i')
  const flexMatch = flex.exec(text)
  if (flexMatch?.index != null) {
    return { start: flexMatch.index, end: flexMatch.index + flexMatch[0].length }
  }

  const minLen = Math.min(trimmedPassage.length, 160)
  for (const len of [minLen, 120, 80, 60, 40].filter((n, i, arr) => n >= 20 && arr.indexOf(n) === i)) {
    const prefix = trimmedPassage.slice(0, len)
    const idx = text.indexOf(prefix)
    if (idx >= 0) {
      const end = Math.min(idx + trimmedPassage.length, text.length)
      return { start: idx, end }
    }
    const prefixFlex = new RegExp(escapeRegExp(prefix).replace(/\s+/g, '\\s+'), 'i')
    const prefixMatch = prefixFlex.exec(text)
    if (prefixMatch?.index != null) {
      const start = prefixMatch.index
      const end = Math.min(start + trimmedPassage.length, text.length)
      if (end - start >= 20) return { start, end }
    }
  }

  return null
}

/**
 * Split `text` into parts with a single highlighted region for the full cited passage when possible.
 */
export function splitTextWithHighlight(text: string, passage: string): TextPart[] {
  const trimmedPassage = passage.trim()
  if (!trimmedPassage) {
    return [{ text, highlight: false }]
  }

  const range = findPassageRange(text, trimmedPassage)
  if (range) {
    const parts: TextPart[] = []
    if (range.start > 0) parts.push({ text: text.slice(0, range.start), highlight: false })
    parts.push({ text: text.slice(range.start, range.end), highlight: true })
    const rest = text.slice(range.end)
    if (rest) parts.push({ text: rest, highlight: false })
    return parts
  }

  return [{ text, highlight: false }]
}
