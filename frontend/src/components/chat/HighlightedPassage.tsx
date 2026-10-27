import { splitTextWithHighlight } from '../../lib/highlightPassage'

export function HighlightedPassage({ text, passage }: { text: string; passage: string }) {
  const parts = splitTextWithHighlight(text, passage)
  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, index) =>
        part.highlight ? (
          <mark
            key={index}
            className="rounded-sm bg-amber-200/95 text-stone-900 shadow-[inset_0_0_0_1px_rgba(251,191,36,0.55)]"
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
