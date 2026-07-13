import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import type { KnowledgeBase } from '../../types/knowledge-base'
import type { Note } from '../../types/note'
import { formatDateTime } from '../../utils/date'

interface NoteDetailProps {
  note: Note | null
  knowledgeBase: KnowledgeBase | null
  isLoading: boolean
  error: string | null
  onEdit: () => void
  onDelete: () => void
  onRetry: () => void
}

export function NoteDetail({
  note,
  knowledgeBase,
  isLoading,
  error,
  onEdit,
  onDelete,
  onRetry,
}: NoteDetailProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-24 text-center text-sm text-slate-400 shadow-sm">
        正在加载笔记详情…
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-16 text-center">
        <p className="text-sm text-rose-700">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700"
        >
          重新加载
        </button>
      </div>
    )
  }

  if (!note) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-24 text-center text-sm text-slate-400 shadow-sm">
        从左侧选择一篇笔记，或创建新的手动笔记。
      </div>
    )
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
      <header className="flex flex-col justify-between gap-4 border-b border-slate-100 pb-5 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                note.source_type === 'agent'
                  ? 'bg-violet-50 text-violet-700'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {note.source_type === 'agent' ? 'Agent 生成' : '手动创建'}
            </span>
            <span className="text-slate-400">
              知识库：{knowledgeBase?.name ?? `#${note.knowledge_base_id}`}
            </span>
            {note.source_type === 'agent' && note.source_agent_task_id !== null && (
              <Link
                to={`/agent?task=${note.source_agent_task_id}`}
                className="font-medium text-violet-700 hover:text-violet-600"
              >
                查看来源任务 →
              </Link>
            )}
          </div>
          <h3 className="mt-3 break-words text-2xl font-semibold text-slate-900">
            {note.title}
          </h3>
          <p className="mt-2 text-xs text-slate-400">
            创建于 {formatDateTime(note.created_at)} · 更新于 {formatDateTime(note.updated_at)}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
          >
            删除
          </button>
        </div>
      </header>

      <div className="mt-6 break-words text-sm leading-7 text-slate-700 [&_blockquote]:border-l-4 [&_blockquote]:border-slate-200 [&_blockquote]:pl-4 [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mt-6 [&_h2]:text-xl [&_h2]:font-semibold [&_h3]:mt-5 [&_h3]:text-lg [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-6 [&_p+p]:mt-4 [&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-slate-100 [&_ul]:list-disc [&_ul]:pl-6">
        <ReactMarkdown>{note.content}</ReactMarkdown>
      </div>
    </article>
  )
}
