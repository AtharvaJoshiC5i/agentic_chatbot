import { ChevronRight } from 'lucide-react'
import { useEffect, useId, useMemo, useState } from 'react'
import type { AgentStep } from '../../api/types'

function ThinkingDots() {
  return (
    <span className="agent-think-dots" aria-hidden>
      <span />
      <span />
      <span />
    </span>
  )
}

function stepSummary(steps: AgentStep[]): string {
  const tools = steps.filter((s) => s.kind === 'tool')
  const running = steps.some((s) => s.status === 'running')
  if (running) return 'Working on your request…'
  if (tools.length > 0) {
    return `Used ${tools.length} tool${tools.length === 1 ? '' : 's'} to gather evidence`
  }
  if (steps.length === 1) return '1 step'
  return `${steps.length} steps`
}

function StatusDot({ status }: { status: string }) {
  if (status === 'running') {
    return (
      <span className="relative flex size-2 shrink-0" aria-hidden>
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent-400/50 motion-reduce:animate-none" />
        <span className="relative inline-flex size-2 rounded-full bg-accent-600" />
      </span>
    )
  }
  return (
    <span
      className={`size-1.5 shrink-0 rounded-full ${status === 'completed' ? 'bg-stone-400' : 'bg-stone-300'}`}
      aria-hidden
    />
  )
}

function IoBlock({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-stone-400">{label}</p>
      <pre className="max-h-36 overflow-auto rounded-md border border-stone-200/90 bg-stone-50/80 px-2.5 py-2 font-mono text-[10px] leading-relaxed whitespace-pre-wrap text-stone-700">
        {text}
      </pre>
    </div>
  )
}

function StepRow({ step, index, isLive }: { step: AgentStep; index: number; isLive: boolean }) {
  const hasIO = Boolean(step.input || step.output)
  const isTool = step.kind === 'tool'
  const running = step.status === 'running'

  return (
    <li
      className={`agent-step-enter py-1 ${running && isLive ? 'agent-step-running -mx-1.5 px-1.5' : ''}`}
      style={{ animationDelay: `${Math.min(index * 55, 320)}ms` }}
    >
      <div className="flex items-start gap-2">
        <span className="mt-1.5 flex w-2 justify-center">
          <StatusDot status={step.status} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p
              className={`text-[12px] leading-snug ${
                running ? 'font-medium text-stone-900' : 'text-stone-800'
              }`}
            >
              {running && isLive ? (
                <span className="agent-think-shimmer">{step.title}</span>
              ) : (
                step.title
              )}
            </p>
            {isTool && step.tool && (
              <span className="hidden shrink-0 font-mono text-[9px] text-stone-400 sm:inline">
                {step.tool}
              </span>
            )}
          </div>
          {step.detail && step.kind !== 'tool' && (
            <p
              className={`mt-0.5 text-[11px] leading-relaxed ${
                running && isLive ? 'text-stone-600' : 'text-stone-500'
              }`}
            >
              {step.detail}
            </p>
          )}
          {hasIO && (
            <details className="group mt-1">
              <summary
                className="cursor-pointer text-[11px] font-medium text-stone-500 select-none hover:text-accent-800"
              >
                <span className="group-open:hidden">View details</span>
                <span className="hidden group-open:inline">Hide details</span>
              </summary>
              <div className="mt-1.5 space-y-2 border-l border-stone-200/90 pl-2.5">
                {step.input && <IoBlock label="Input" text={step.input} />}
                {step.output && <IoBlock label="Output" text={step.output} />}
              </div>
            </details>
          )}
        </div>
      </div>
    </li>
  )
}

/** Shown before the first streamed step arrives. */
export function AgentThinkingPlaceholder() {
  return (
    <section className="mb-3" aria-live="polite" aria-label="Agent thinking">
      <div className="flex items-center gap-2 py-1.5">
        <span className="agent-think-shimmer text-[12px] font-medium">Thinking</span>
        <ThinkingDots />
      </div>
      <p className="text-[11px] text-stone-500">Understanding your question…</p>
    </section>
  )
}

export function AgentTrace({
  steps,
  live = false,
  showFinalLabel = false,
  collapsedWhenStreaming = false,
}: {
  steps: AgentStep[]
  live?: boolean
  showFinalLabel?: boolean
  /** Collapse the step list while the answer text is streaming (Claude-style). */
  collapsedWhenStreaming?: boolean
}) {
  const panelId = useId()
  const [open, setOpen] = useState(live)
  const ordered = useMemo(
    () => [...steps].sort((a, b) => a.index - b.index),
    [steps],
  )

  const running = ordered.some((s) => s.status === 'running')
  const isThinking = live && (running || ordered.length > 0)
  const summary = stepSummary(ordered)
  const activeStep = ordered.find((s) => s.status === 'running') ?? ordered[ordered.length - 1]

  useEffect(() => {
    if (live && !collapsedWhenStreaming) setOpen(true)
  }, [live, collapsedWhenStreaming])

  useEffect(() => {
    if (collapsedWhenStreaming) setOpen(false)
  }, [collapsedWhenStreaming])

  if (!ordered.length) return null

  const panelOpen = open && !collapsedWhenStreaming

  return (
    <section className="mb-3" aria-label="Agent activity" aria-live={live ? 'polite' : undefined}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={panelOpen}
        aria-controls={panelId}
        className="group flex w-full items-center gap-1.5 rounded-md py-1 text-left transition-colors hover:bg-stone-100/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
      >
        <ChevronRight
          className={`size-3.5 shrink-0 text-stone-400 transition-transform duration-200 group-hover:text-stone-600 ${panelOpen ? 'rotate-90' : ''}`}
          strokeWidth={1.75}
          aria-hidden
        />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            {isThinking ? (
              <span className="agent-think-shimmer text-[12px] font-medium">Thinking</span>
            ) : (
              <span className="text-[12px] font-medium text-stone-700">Activity</span>
            )}
            {isThinking && <ThinkingDots />}
            {!panelOpen && !isThinking && (
              <span className="truncate text-[11px] text-stone-500">{summary}</span>
            )}
            {!panelOpen && isThinking && activeStep && (
              <span className="truncate text-[11px] text-stone-500">{activeStep.title}</span>
            )}
          </span>
        </span>
        {panelOpen && (
          <span className="shrink-0 text-[10px] tabular-nums text-stone-400">{ordered.length}</span>
        )}
      </button>

      <div
        id={panelId}
        hidden={!panelOpen}
        className={`ml-2.5 border-l pl-3 ${isThinking ? 'agent-timeline-live border-accent-200/90' : 'border-stone-200/80'}`}
      >
        <ol className="py-0.5">
          {ordered.map((step, index) => (
            <StepRow
              key={`${step.index}-${step.kind}-${step.title}`}
              step={step}
              index={index}
              isLive={live}
            />
          ))}
        </ol>
        {showFinalLabel && !live && (
          <p className="border-t border-stone-100 py-2 text-[10px] text-stone-400">Answer</p>
        )}
      </div>
    </section>
  )
}
