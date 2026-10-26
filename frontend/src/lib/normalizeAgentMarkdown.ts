/**
 * Fixes common agent markdown so headings, category labels, and sub-bullets render with clear hierarchy.
 */

const BULLET_RE = /^(\s*)[-*]\s+(.*)$/

/** Line is only a bold category label, e.g. `**Damaged on arrival:**` */
function isCategoryLabelOnly(text: string): boolean {
  const t = text.trim()
  return /^\*\*[^*]+\*\*\s*:?\s*$/.test(t)
}

/** Top-level category row with inline value, e.g. `**Return window:** 30 days` */
function isCategoryWithInlineValue(text: string): boolean {
  const t = text.trim()
  return /^\*\*[^*]+\*\*\s*:\s*\S/.test(t)
}

function isNewCategoryBullet(text: string): boolean {
  return isCategoryLabelOnly(text) || isCategoryWithInlineValue(text)
}

/** Nest plain follow-up bullets under a label-only category line. */
export function nestBulletsUnderCategoryLabels(markdown: string): string {
  const lines = markdown.split('\n')
  const out: string[] = []
  let nesting = false

  for (const line of lines) {
    const match = BULLET_RE.exec(line)
    if (!match) {
      nesting = false
      out.push(line)
      continue
    }

    const content = match[2]
    if (isCategoryLabelOnly(content)) {
      nesting = true
      out.push(line)
      continue
    }

    if (nesting && !isNewCategoryBullet(content)) {
      out.push(`  - ${content}`)
      continue
    }

    nesting = false
    out.push(line)
  }

  return out.join('\n')
}

/** Turn `1. Electronics (POL-…)` into a ### heading when not already a list item. */
export function promoteEnumeratedSectionHeadings(markdown: string): string {
  return markdown
    .split('\n')
    .map((line) => {
      if (/^#{1,6}\s/.test(line)) return line
      if (/^\s*[-*]\s/.test(line)) return line
      if (/^\s*\d+\.\s/.test(line) && line.startsWith(' ')) return line
      const trimmed = line.trim()
      const m = /^(\d+)\.\s+(.+)$/.exec(trimmed)
      if (m) return `### ${m[1]}. ${m[2]}`
      return line
    })
    .join('\n')
}

export function normalizeAgentMarkdown(markdown: string): string {
  let text = markdown.trim()
  if (!text) return text
  text = promoteEnumeratedSectionHeadings(text)
  text = nestBulletsUnderCategoryLabels(text)
  return text
}
