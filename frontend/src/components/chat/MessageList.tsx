import type { AgentStep } from '../../api/types'
import type { ChatMessage } from '../../lib/chats'
import type { ChatVisual } from '../../lib/visuals'
import { resolveMessageEvidence } from '../../lib/supportingEvidence'
import { BrandMark } from '../ui/BrandMark'
import { AgentThinkingPlaceholder, AgentTrace } from './AgentTrace'
import { ChatVisuals } from './visuals/ChatVisuals'
import { MarkdownBody, StreamingMarkdown } from './MarkdownBody'
import { SupportingEvidence } from './SupportingEvidence'

function AssistantRow({ children }: { children: React.ReactNode }) {
  return (
    <article className="flex gap-3">
      <BrandMark className="mt-0.5 size-6 shrink-0 rounded-md" tone="brand" />
      <div className="min-w-0 flex-1 space-y-3">{children}</div>
    </article>
  )
}

export function MessageList({
  messages,
  pending,
  liveAgentSteps,
  streamingContent,
  onUpdateMessageVisuals,
}: {
  messages: ChatMessage[]
  pending: boolean
  liveAgentSteps: AgentStep[]
  streamingContent: string | null
  onUpdateMessageVisuals?: (messageId: string, visuals: ChatVisual[]) => void
}) {
  const isStreaming = pending && streamingContent !== null
  const showStreamText = isStreaming && streamingContent.length > 0

  return (
    <div className="mx-auto w-full max-w-3xl space-y-7 px-4 py-8 sm:px-6 lg:max-w-4xl lg:px-8">
      {messages.map((msg) =>
        msg.role === 'user' ? (
          <article key={msg.id} className="flex justify-end">
            <p className="chat-user-bubble max-w-[min(85%,32rem)] px-4 py-2.5 text-sm leading-6 whitespace-pre-wrap">
              {msg.content}
            </p>
          </article>
        ) : (
          <AssistantRow key={msg.id}>
            {msg.agentSteps && msg.agentSteps.length > 0 && (
              <AgentTrace steps={msg.agentSteps} showFinalLabel={Boolean(msg.content)} />
            )}
            {msg.content ? <MarkdownBody content={msg.content} /> : null}
            {msg.visuals && msg.visuals.length > 0 && (
              <ChatVisuals
                visuals={msg.visuals}
                onVisualAtIndex={
                  onUpdateMessageVisuals
                    ? (index, next) => {
                        const updated = msg.visuals!.map((item, j) => (j === index ? next : item))
                        onUpdateMessageVisuals(msg.id, updated)
                      }
                    : undefined
                }
              />
            )}
            <SupportingEvidence bundle={resolveMessageEvidence(msg)} />
            {msg.provider && (
              <p className="mt-1 text-[11px] text-stone-400">
                {msg.provider}
                {msg.model ? ` · ${msg.model}` : ''}
              </p>
            )}
          </AssistantRow>
        ),
      )}
      {pending && (
        <AssistantRow>
          {liveAgentSteps.length > 0 && (
            <AgentTrace steps={liveAgentSteps} live collapsedWhenStreaming={showStreamText} />
          )}
          {showStreamText ? (
            <StreamingMarkdown content={streamingContent} />
          ) : liveAgentSteps.length === 0 ? (
            <AgentThinkingPlaceholder />
          ) : null}
        </AssistantRow>
      )}
    </div>
  )
}
