import { Link } from 'react-router-dom'
import type { KnowledgeBase } from '../../types/knowledge-base'
import { formatDateTime } from '../../utils/date'

interface KnowledgeBaseCardProps {
  knowledgeBase: KnowledgeBase
  onEdit: (knowledgeBase: KnowledgeBase) => void
  onDelete: (knowledgeBase: KnowledgeBase) => void
}

export function KnowledgeBaseCard({
  knowledgeBase,
  onEdit,
  onDelete,
}: KnowledgeBaseCardProps) {
  return (
    <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-medium text-indigo-600">知识库</p>
          <Link
            to={`/knowledge-bases/${knowledgeBase.id}`}
            className="mt-1 block truncate text-lg font-semibold text-slate-900 hover:text-indigo-600"
          >
            {knowledgeBase.name}
          </Link>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-500">
          #{knowledgeBase.id}
        </span>
      </div>

      <p className="mt-4 line-clamp-3 min-h-15 flex-1 text-sm leading-6 text-slate-500">
        {knowledgeBase.description || '暂无描述'}
      </p>

      <dl className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-400">
        <div className="flex justify-between gap-3">
          <dt>创建时间</dt>
          <dd className="text-right">{formatDateTime(knowledgeBase.created_at)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>更新时间</dt>
          <dd className="text-right">{formatDateTime(knowledgeBase.updated_at)}</dd>
        </div>
      </dl>

      <div className="mt-5 flex gap-2">
        <Link
          to={`/knowledge-bases/${knowledgeBase.id}`}
          className="flex-1 rounded-lg bg-slate-900 px-3 py-2 text-center text-sm font-medium text-white transition hover:bg-slate-700"
        >
          查看详情
        </Link>
        <button
          type="button"
          onClick={() => onEdit(knowledgeBase)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
        >
          编辑
        </button>
        <button
          type="button"
          onClick={() => onDelete(knowledgeBase)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"
        >
          删除
        </button>
      </div>
    </article>
  )
}
