import { FileText, Mail } from 'lucide-react'

function PdfGlyph({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-[10px] font-bold tracking-tight text-red-700 ring-1 ring-red-200 ${className ?? ''}`}
      aria-hidden
    >
      PDF
    </span>
  )
}

function DocxGlyph({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-blue-50 ring-1 ring-blue-200 ${className ?? ''}`}
      aria-hidden
    >
      <FileText className="size-4 text-blue-700" strokeWidth={1.75} />
    </span>
  )
}

export function DocumentFileIcon({ fileKind, className }: { fileKind: string; className?: string }) {
  const kind = fileKind.toLowerCase()
  if (kind === 'pdf') {
    return <PdfGlyph className={className} />
  }
  if (kind === 'docx' || kind === 'doc') {
    return <DocxGlyph className={className} />
  }
  if (kind === 'eml') {
    return (
      <span
        className={`inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-stone-100 ring-1 ring-stone-200 ${className ?? ''}`}
        aria-hidden
      >
        <Mail className="size-4 text-stone-600" strokeWidth={1.75} />
      </span>
    )
  }
  return (
    <span
      className={`inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-stone-100 ring-1 ring-stone-200 ${className ?? ''}`}
      aria-hidden
    >
      <FileText className="size-4 text-stone-600" strokeWidth={1.75} />
    </span>
  )
}
