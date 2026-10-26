import type { Conversation } from './chats'

export type ConversationGroup = {
  label: string
  items: Conversation[]
}

function startOfDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

export function groupConversationsByDate(conversations: Conversation[]): ConversationGroup[] {
  const now = new Date()
  const today = startOfDay(now).getTime()
  const yesterday = today - 86_400_000
  const weekAgo = today - 7 * 86_400_000

  const sorted = [...conversations].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  )

  const todayItems: Conversation[] = []
  const yesterdayItems: Conversation[] = []
  const weekItems: Conversation[] = []
  const olderItems: Conversation[] = []

  for (const c of sorted) {
    const t = new Date(c.updatedAt).getTime()
    if (t >= today) todayItems.push(c)
    else if (t >= yesterday) yesterdayItems.push(c)
    else if (t >= weekAgo) weekItems.push(c)
    else olderItems.push(c)
  }

  const groups: ConversationGroup[] = []
  if (todayItems.length) groups.push({ label: 'Today', items: todayItems })
  if (yesterdayItems.length) groups.push({ label: 'Yesterday', items: yesterdayItems })
  if (weekItems.length) groups.push({ label: 'Previous 7 days', items: weekItems })
  if (olderItems.length) groups.push({ label: 'Older', items: olderItems })
  return groups
}
