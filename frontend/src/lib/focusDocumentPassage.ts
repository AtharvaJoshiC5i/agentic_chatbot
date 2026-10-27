/** Scroll a rendered unstructured document to its cited text and highlight the match. */
export function focusDocumentPassage(root: ParentNode, passage: string): HTMLElement | null {
  const candidates = [120, 60, 30]
    .map((length) => passage.trim().slice(0, length))
    .filter((candidate, index, all) => candidate.length >= 12 && all.indexOf(candidate) === index)
  if (!candidates.length) return null

  const owner = root instanceof Document ? root : root.ownerDocument
  if (!owner) return null
  const walker = owner.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node: Node | null
  while ((node = walker.nextNode())) {
    const text = node.textContent ?? ''
    const lower = text.toLocaleLowerCase()
    const candidate = candidates.find((item) => lower.includes(item.toLocaleLowerCase()))
    if (!candidate || !node.parentElement) continue

    const start = lower.indexOf(candidate.toLocaleLowerCase())
    const range = owner.createRange()
    range.setStart(node, start)
    range.setEnd(node, start + candidate.length)
    const mark = owner.createElement('mark')
    mark.setAttribute('data-cited-passage', 'true')
    mark.style.cssText = 'background:#fde68a;color:#18181b;border-radius:2px;padding:0 2px'
    try {
      range.surroundContents(mark)
      mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return mark
    } catch {
      node.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return node.parentElement
    }
  }

  const normalizedPassage = passage.trim().replace(/\s+/g, ' ').slice(0, 40).toLocaleLowerCase()
  const blocks = root instanceof Element
    ? root.querySelectorAll('p, li, td, th, blockquote, pre, h1, h2, h3, h4')
    : root.querySelectorAll('p, li, td, th, blockquote, pre, h1, h2, h3, h4')
  for (const block of blocks) {
    const text = block.textContent?.replace(/\s+/g, ' ').toLocaleLowerCase() ?? ''
    if (normalizedPassage.length >= 12 && text.includes(normalizedPassage)) {
      block.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return block as HTMLElement
    }
  }
  return null
}
