import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import type { AgentTask } from '../../types/agent'
import type { Note } from '../../types/note'
import {
  agentTaskStatusViews,
  agentTaskTypeLabels,
  getAgentTaskErrorMessage,
} from '../../utils/agent'
import { CitationList } from '../chat/CitationList'

interface AgentTaskResultProps {
  task: AgentTask | null
  knowledgeBaseName: string | null
  isLoading: boolean
  loadError: string | null
  isRetrying: boolean
  isSavingNote: boolean
  actionError: string | null
  savedNote: Note | null
  onRetry: () => void
  onSaveNote: () => void
  onReload: () => void
}

export function AgentTaskResult({
  task,
  knowledgeBaseName,
  isLoading,
  loadError,
  isRetrying,
  isSavingNote,
  actionError,
  savedNote,
  onRetry,
  onSaveNote,
  onReload,
}: AgentTaskResultProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-24 text-center text-sm text-slate-400 shadow-sm">
        正在加载任务详情…
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-16 text-center">
        <p className="text-sm text-rose-700">{loadError}</p>
        <button
          type="button"
          onClick={onReload}
          className="mt-4 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700"
        >
          重新加载
        </button>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-24 text-center text-sm text-slate-400 shadow-sm">
        执行一个新任务，或从左侧选择历史任务查看结果。
      </div>
    )
  }

  const statusView = agentTaskStatusViews[task.status]

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <header className="flex flex-col justify-between gap-3 border-b border-slate-100 pb-5 sm:flex-row sm:items-start">
        <div>
          <p className="text-sm font-semibold text-indigo-700">
            {agentTaskTypeLabels[task.task_type]}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">Agent 任务 #{task.id}</h3>
          <p className="mt-1 text-xs text-slate-400">
            知识库：{knowledgeBaseName ?? `#${task.knowledge_base_id}`}
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-500">
            {task.task_input}
          </p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-xs font-medium ${statusView.className}`}>
          {statusView.label}
        </span>
      </header>

      {task.status === 'running' || task.status === 'pending' ? (
        <p className="py-16 text-center text-sm text-amber-700">任务正在执行，请稍候…</p>
      ) : task.status === 'failed' ? (
        <div className="py-10 text-center">
          <p className="text-sm text-rose-700">
            {getAgentTaskErrorMessage(task.error_message)}
          </p>
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="mt-4 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
          >
            {isRetrying ? '正在重新执行…' : '重试任务'}
          </button>
        </div>
      ) : (
        <div className="space-y-6 pt-6">
          <div>
            <p className="text-sm font-semibold text-slate-800">任务结果</p>
            <div className="mt-3 rounded-xl bg-slate-50 p-5 text-sm leading-7 text-slate-700 [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:mt-5 [&_h2]:text-lg [&_h2]:font-semibold [&_ol]:list-decimal [&_ol]:pl-6 [&_p+p]:mt-3 [&_ul]:list-disc [&_ul]:pl-6">
              <ReactMarkdown>{task.result_content ?? ''}</ReactMarkdown>
            </div>
          </div>
          <CitationList
            citations={task.citations}
            title="任务引用来源"
            emptyMessage="本次任务没有可展示的引用来源。"
          />
          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
            <button
              type="button"
              onClick={onSaveNote}
              disabled={isSavingNote}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {isSavingNote ? '正在保存…' : '保存为笔记'}
            </button>
            {savedNote && (
              <Link
                to={`/notes?note=${savedNote.id}`}
                className="text-sm font-medium text-emerald-700 hover:text-emerald-600"
              >
                已保存为“{savedNote.title}”，查看笔记 →
              </Link>
            )}
          </div>
        </div>
      )}

      {actionError && (
        <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {actionError}
        </p>
      )}
    </section>
  )
}
