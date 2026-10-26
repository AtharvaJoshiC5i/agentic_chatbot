/** Per-login chat isolation in localStorage (keyed by username from auth). */

const STORAGE_PREFIX = 'shopsphere_chats_v3'
const LEGACY_V1_KEY = 'shopsphere_conversations_v1'
const LEGACY_V2_PREFIX = 'shopsphere_conversations_v2'
const LEGACY_MIGRATED_FLAG = 'shopsphere_chats_legacy_migrated_v1'

export function normalizeChatAccount(username: string): string {
  return username.trim().toLowerCase()
}

export function chatStorageKey(username: string): string {
  const id = normalizeChatAccount(username).replace(/[^a-z0-9_@.-]/g, '_')
  if (!id) throw new Error('chatStorageKey requires a non-empty username')
  return `${STORAGE_PREFIX}_${id}`
}

/** One-time import of pre–per-user localStorage into the first account that loads after upgrade. */
export function importLegacyConversationsIfNeeded(username: string): string | null {
  const key = chatStorageKey(username)
  if (localStorage.getItem(key)) return null
  if (localStorage.getItem(LEGACY_MIGRATED_FLAG)) return null

  const legacyV1 = localStorage.getItem(LEGACY_V1_KEY)
  if (legacyV1) {
    localStorage.setItem(key, legacyV1)
    localStorage.removeItem(LEGACY_V1_KEY)
    localStorage.setItem(LEGACY_MIGRATED_FLAG, normalizeChatAccount(username))
    return legacyV1
  }

  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i)
    if (!k?.startsWith(`${LEGACY_V2_PREFIX}_`)) continue
    const data = localStorage.getItem(k)
    if (data) {
      localStorage.setItem(key, data)
      localStorage.setItem(LEGACY_MIGRATED_FLAG, normalizeChatAccount(username))
      return data
    }
  }

  return null
}
