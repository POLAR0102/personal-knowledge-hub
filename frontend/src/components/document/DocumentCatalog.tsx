import { Link } from 'react-router-dom'
import type { KnowledgeDocument } from '../../types/document'
import type { KnowledgeBase } from '../../types/knowledge-base'
import { formatDateTime } from '../../utils/date'
import { formatFileSize } from '../../utils/file'

const statusViews = {
  pending: { label: '等待处理', className: 'bg-amber-50 text-amber-700' },
  processing: { label: '处理中', className: 'bg-blue-50 text-blue-700' },
  completed: { label: '处理完成', className: 'bg-emerald-50 text-emerald-700' },
  failed: { label: '处理失败', className: 'bg-rose-50 text-rose-700' },
}

interface DocumentCatalogProps {
  documents: KnowledgeDocument[]
  knowledgeBases: KnowledgeBase[]
  updatingFavoriteId: number | null
  onToggleFavorite: (document: KnowledgeDocument) => void
  onManageTags: (document: KnowledgeDocument) => void
}

export function DocumentCatalog({
  documents,
  knowledgeBases,
  updatingFavoriteId,
  onToggleFavorite,
  onManageTags,
}: DocumentCatalogProps) {
  const knowledgeBaseNames = new Map(
    knowledgeBases.map((knowledgeBase) => [knowledgeBase.id, knowledgeBase.name]),
  )

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {documents.map((document) => {
        const status = statusViews[document.status]
        return (
          <article
            key={document.id}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="break-words font-semibold text-slate-900">
                  {document.original_filename}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {knowledgeBaseNames.get(document.knowledge_base_id) ??
                    `知识库 #${document.knowledge_base_id}`}
                </p>
              </div>
              <button
                type="button"
                aria-label={document.is_favorite ? '取消收藏' : '收藏文档'}
                onClick={() => onToggleFavorite(document)}
                disabled={updatingFavoriteId !== null}
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-lg transition disabled:opacity-50 ${
                  document.is_favorite
                    ? 'bg-amber-100 text-amber-600'
                    : 'bg-slate-100 text-slate-400 hover:text-amber-600'
                }`}
              >
                {updatingFavoriteId === document.id ? '…' : '★'}
              </button>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className={`rounded-full px-2 py-1 ${status.className}`}>
                {status.label}
              </span>
              <span className="text-slate-400">
                {document.file_type.toUpperCase()} · {formatFileSize(document.file_size)}
              </span>
            </div>

            <div className="mt-4 flex min-h-7 flex-wrap gap-2">
              {document.tags.length === 0 ? (
                <span className="text-xs text-slate-400">暂无标签</span>
              ) : (
                document.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700"
                  >
                    {tag.name}
                  </span>
                ))
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
              <span className="text-xs text-slate-400">
                上传于 {formatDateTime(document.created_at)}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => onManageTags(document)}
                  className="rounded-lg border border-indigo-200 px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                >
                  设置标签
                </button>
                <Link
                  to={`/knowledge-bases/${document.knowledge_base_id}`}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  进入知识库
                </Link>
              </div>
            </div>
          </article>
        )
      })}
    </div>
  )
}
