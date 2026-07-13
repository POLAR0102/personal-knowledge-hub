import { useState } from 'react'
import type { RagCitation } from '../../types/rag'

interface CitationCardProps {
  citation: RagCitation
}

export function CitationCard({ citation }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <article className="rounded-xl border border-slate-200 bg-white">
      <button
        type="button"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((current) => !current)}
        className="flex w-full items-start justify-between gap-4 px-4 py-3 text-left"
      >
        <span>
          <span className="text-sm font-semibold text-slate-800">
            来源 {citation.source_number} · {citation.filename}
          </span>
          <span className="mt-1 block text-xs text-slate-500">
            Chunk #{citation.chunk_index}
            {citation.page_number !== null && ` · 第 ${citation.page_number} 页`}
            {citation.section_title && ` · ${citation.section_title}`}
          </span>
        </span>
        <span className="shrink-0 text-xs font-medium text-indigo-600">
          {isExpanded ? '收起' : '展开原文'}
        </span>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-100 px-4 py-4">
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-700">
            {citation.content}
          </pre>
          <p className="mt-3 text-xs text-slate-400">
            cosine distance：{citation.distance.toFixed(4)}（越小通常越相关）
          </p>
        </div>
      )}
    </article>
  )
}
