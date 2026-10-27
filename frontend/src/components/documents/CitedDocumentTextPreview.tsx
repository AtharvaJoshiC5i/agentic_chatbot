import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import { api } from '../../api/client'
import type { DocumentPreview } from '../../api/types'
import { findPassageRange } from '../../lib/highlightPassage'
import { HighlightedPassage } from '../chat/HighlightedPassage'

const HIGHLIGHT_MARK_CLASS =
  'rounded-sm bg-amber-200/95 text-stone-900 shadow-[inset_0_0_0_1px_rgba(251,191,36,0.55)]'

export function CitedDocumentTextPreview({
  documentId,
  filename,
  passage,
  page,
}: {
  documentId: number
  filename: string
  passage: string
  page?: number | null
}) {
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const highlightRef = useRef<HTMLSpanElement | null>(null)
  const pageRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .documentPreview(documentId)
      .then((data) => {
        if (!cancelled) setPreview(data)
      })
      .catch(() => {
        if (!cancelled) {
          setPreview(null)
          setError('Could not load document text for citation preview.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [documentId])

  useEffect(() => {
    const t = window.setTimeout(() => {
      if (pageRef.current) {
        pageRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
      highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 150)
    return () => window.clearTimeout(t)
  }, [preview, passage, page])

  const segments = useMemo(() => {
    if (!preview) return []
    if (preview.segments.length) return preview.segments
    return [{ page: page ?? null, section: null, text: preview.full_text }]
  }, [preview, page])

  const passageRange = useMemo(
    () => (preview ? findPassageRange(preview.full_text, passage) : null),
    [preview, passage],
  )

  const segmentStarts = useMemo(() => {
    const starts: number[] = []
    let offset = 0
    segments.forEach((segment, index) => {
      starts.push(offset)
      offset += segment.text.length
      if (index < segments.length - 1) offset += 2
    })
    return starts
  }, [segments])

  if (loading) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center bg-zinc-100">
        <p className="text-sm text-zinc-500">Loading document…</p>
      </div>
    )
  }

  if (error || !preview) {
    return (
      <p className="m-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {error ?? 'Preview unavailable.'}
      </p>
    )
  }

  const targetPage = page && page > 0 ? page : null

  return (
    <div className="h-full min-h-0 overflow-y-auto bg-zinc-200/80 px-4 py-5 sm:px-6">
      <p className="mb-4 text-center text-[11px] font-medium text-zinc-500">{filename}</p>
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {segments.map((segment, index) => {
          const segmentStart = segmentStarts[index] ?? 0
          const isTargetPage =
            targetPage != null && segment.page != null && segment.page === targetPage
          const showPage =
            segment.page != null &&
            (index === 0 || segments[index - 1]?.page !== segment.page)

          return (
            <div
              key={`${segment.page ?? 'n'}-${index}`}
              ref={isTargetPage ? pageRef : undefined}
              className="rounded-lg border border-zinc-200/90 bg-white shadow-sm"
            >
              {showPage && (
                <div className="border-b border-zinc-100 px-5 py-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
                  Page {segment.page}
                  {segment.section ? ` · ${segment.section}` : ''}
                </div>
              )}
              <div className="px-6 py-5 font-serif text-[15px] leading-[1.65] text-zinc-900">
                <SegmentPassage
                  text={segment.text}
                  passage={passage}
                  segmentStart={segmentStart}
                  passageRange={passageRange}
                  highlightRef={
                    passageRange &&
                    passageRange.start >= segmentStart &&
                    passageRange.start < segmentStart + segment.text.length
                      ? highlightRef
                      : undefined
                  }
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SegmentPassage({
  text,
  passage,
  segmentStart,
  passageRange,
  highlightRef,
}: {
  text: string
  passage: string
  segmentStart: number
  passageRange: { start: number; end: number } | null
  highlightRef?: RefObject<HTMLSpanElement | null>
}) {
  const trimmed = passage.trim()
  if (!trimmed) {
    return <p className="whitespace-pre-wrap">{text}</p>
  }

  const range = passageRange
  if (!range) {
    return (
      <p className="whitespace-pre-wrap">
        <HighlightedPassage text={text} passage={trimmed} />
      </p>
    )
  }

  const localStart = Math.max(0, range.start - segmentStart)
  const localEnd = Math.min(text.length, range.end - segmentStart)
  if (localEnd <= localStart) {
    return <p className="whitespace-pre-wrap">{text}</p>
  }

  const before = text.slice(0, localStart)
  const cited = text.slice(localStart, localEnd)
  const after = text.slice(localEnd)

  return (
    <p className="whitespace-pre-wrap">
      {before}
      <mark ref={highlightRef} className={HIGHLIGHT_MARK_CLASS}>{cited}</mark>
      {after}
    </p>
  )
}
