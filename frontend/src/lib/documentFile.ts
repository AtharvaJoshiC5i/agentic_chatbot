import { getStoredToken } from '../api/client'

export async function fetchDocumentBlob(documentId: number): Promise<Blob> {
  const token = getStoredToken()
  const res = await fetch(`/api/documents/${documentId}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new Error('Could not load document file')
  }
  return res.blob()
}

export async function fetchDocumentHtmlPreview(documentId: number): Promise<string> {
  const token = getStoredToken()
  const res = await fetch(`/api/documents/${documentId}/preview-html`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new Error('Could not load HTML preview')
  }
  return res.text()
}

export async function openDocumentInNewTab(documentId: number): Promise<void> {
  const blob = await fetchDocumentBlob(documentId)
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
}
