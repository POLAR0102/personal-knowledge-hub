import type { RagCitation } from '../../types/rag'
import { CitationCard } from './CitationCard'

interface CitationListProps {
  citations: RagCitation[]
}

export function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) {
    return (
      <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
        本次回答没有可展示的引用来源。
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-slate-800">
        引用来源（{citations.length}）
      </p>
      {citations.map((citation) => (
        <CitationCard key={citation.chunk_id} citation={citation} />
      ))}
    </div>
  )
}
