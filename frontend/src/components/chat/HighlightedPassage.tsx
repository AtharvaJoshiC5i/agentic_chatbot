import { splitTextWithHighlight } from '../../lib/highlightPassage'

export function HighlightedPassage({ text, passage }: { text: string; passage: string }) {
  const parts = splitTextWithHighlight(text, passage)
  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, index) =>
        part.highlight ? (
          <mark
            key={index}
            className="rounded-sm bg-amber-200/90 px-0.5 text-stone-900 ring-1 ring-amber-300/80"
          >
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </span>
  )
}
