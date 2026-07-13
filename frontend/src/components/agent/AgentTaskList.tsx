import type { AgentTask } from '../../types/agent'
import { agentTaskStatusViews, agentTaskTypeLabels } from '../../utils/agent'
import { formatDateTime } from '../../utils/date'

interface AgentTaskListProps {
  tasks: AgentTask[]
  total: number
  activeTaskId: number | null
  isLoading: boolean
  error: string | null
  disabled: boolean
  onSelect: (taskId: number) => void
  onRetryLoad: () => void
}

export function AgentTaskList({
  tasks,
  total,
  activeTaskId,
  isLoading,
  error,
  disabled,
  onSelect,
  onRetryLoad,
}: AgentTaskListProps) {
  return (
    <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h3 className="font-semibold text-slate-900">历史任务</h3>
        <p className="mt-1 text-xs text-slate-400">共 {total} 个任务</p>
      </div>

      <div className="mt-4 space-y-2 lg:max-h-[48rem] lg:overflow-y-auto lg:pr-1">
        {isLoading ? (
          <p className="py-10 text-center text-sm text-slate-400">正在加载任务…</p>
        ) : error ? (
          <div className="rounded-xl bg-rose-50 p-4 text-center">
            <p className="text-sm text-rose-700">{error}</p>
            <button
              type="button"
              onClick={onRetryLoad}
              className="mt-3 text-xs font-semibold text-rose-700 underline"
            >
              重新加载
            </button>
          </div>
        ) : tasks.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-400">
            暂无 Agent 任务
          </p>
        ) : (
          tasks.map((task) => {
            const statusView = agentTaskStatusViews[task.status]
            return (
              <button
                key={task.id}
                type="button"
                onClick={() => onSelect(task.id)}
                disabled={disabled}
                className={`w-full rounded-xl border p-3 text-left transition disabled:cursor-not-allowed ${
                  task.id === activeTaskId
                    ? 'border-indigo-200 bg-indigo-50'
                    : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-indigo-700">
                    {agentTaskTypeLabels[task.task_type]}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] ${statusView.className}`}>
                    {statusView.label}
                  </span>
                </span>
                <span className="mt-2 block truncate text-sm text-slate-700">
                  {task.task_input}
                </span>
                <span className="mt-1 block text-xs text-slate-400">
                  {formatDateTime(task.created_at)}
                </span>
              </button>
            )
          })
        )}
      </div>
    </aside>
  )
}
