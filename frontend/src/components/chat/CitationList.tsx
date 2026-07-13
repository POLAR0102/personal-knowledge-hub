import type { RagCitation } from '../../types/rag'
import { CitationCard } from './CitationCard'

interface CitationListProps {
  citations: RagCitation[]
  title?: string
  emptyMessage?: string
}

export function CitationList({
  citations,
  title = '引用来源',
  emptyMessage = '本次回答没有可展示的引用来源。',
}: CitationListProps) {
  if (citations.length === 0) {
    return (
      <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
        {emptyMessage}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-slate-800">
        {title}（{citations.length}）
      </p>
      {citations.map((citation) => (
        <CitationCard key={citation.chunk_id} citation={citation} />
      ))}
    </div>
  )
}
