import type { KnowledgeDocument } from '../../types/document'

const indexStatusView = {
  not_indexed: { label: '未索引', className: 'bg-slate-100 text-slate-600' },
  indexing: { label: '索引中', className: 'bg-blue-50 text-blue-700' },
  indexed: { label: '已索引', className: 'bg-emerald-50 text-emerald-700' },
  failed: { label: '索引失败', className: 'bg-rose-50 text-rose-700' },
}

interface DocumentIndexActionsProps {
  document: KnowledgeDocument
  indexingDocumentId: number | null
  onIndex: (document: KnowledgeDocument) => void
  onViewStatus: (document: KnowledgeDocument) => void
}

export function DocumentIndexActions({
  document,
  indexingDocumentId,
  onIndex,
  onViewStatus,
}: DocumentIndexActionsProps) {
  const view = indexStatusView[document.index_status]
  const isSubmitting = indexingDocumentId === document.id
  const canIndex = document.status === 'completed'

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={`rounded-full px-2 py-0.5 text-xs ${view.className}`}>
        {isSubmitting ? '索引中' : view.label}
      </span>
      {document.embedding_model && document.index_status === 'indexed' && (
        <span className="text-xs text-slate-400">{document.embedding_model}</span>
      )}
      {canIndex && document.index_status !== 'indexing' && (
        <button
          type="button"
          disabled={indexingDocumentId !== null}
          onClick={() => onIndex(document)}
          className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting
            ? '正在建立索引…'
            : document.index_status === 'not_indexed'
              ? '建立索引'
              : '重新索引'}
        </button>
      )}
      {document.index_status === 'indexing' && (
        <button
          type="button"
          disabled
          className="rounded-lg bg-blue-50 px-3 py-2 text-xs font-medium text-blue-600 opacity-70"
        >
          正在建立索引…
        </button>
      )}
      {canIndex && document.index_status !== 'not_indexed' && (
        <button
          type="button"
          onClick={() => onViewStatus(document)}
          className="rounded-lg border border-violet-200 px-3 py-2 text-xs font-medium text-violet-700 hover:bg-violet-50"
        >
          索引详情
        </button>
      )}
    </div>
  )
}
