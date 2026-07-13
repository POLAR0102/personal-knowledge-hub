import type { Conversation } from '../../types/conversation'
import { formatDateTime } from '../../utils/date'

interface ConversationSidebarProps {
  conversations: Conversation[]
  total: number
  activeConversationId: number | null
  disabled: boolean
  isLoading: boolean
  error: string | null
  onCreate: () => void
  onSelect: (conversationId: number) => void
  onDelete: (conversation: Conversation) => void
  onRetry: () => void
}

export function ConversationSidebar({
  conversations,
  total,
  activeConversationId,
  disabled,
  isLoading,
  error,
  onCreate,
  onSelect,
  onDelete,
  onRetry,
}: ConversationSidebarProps) {
  return (
    <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">问答会话</h3>
          <p className="mt-1 text-xs text-slate-400">共 {total} 个会话</p>
        </div>
        <button
          type="button"
          onClick={onCreate}
          disabled={disabled}
          className="shrink-0 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          + 新建
        </button>
      </div>

      <div className="mt-4 space-y-2 lg:max-h-[40rem] lg:overflow-y-auto lg:pr-1">
        {isLoading ? (
          <p className="py-10 text-center text-sm text-slate-400">正在加载会话…</p>
        ) : error ? (
          <div className="rounded-xl bg-rose-50 p-4 text-center">
            <p className="text-sm text-rose-700">{error}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 text-xs font-semibold text-rose-700 underline"
            >
              重新加载
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm leading-6 text-slate-400">
            还没有问答会话，点击“新建”开始。
          </p>
        ) : (
          conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId
            return (
              <div
                key={conversation.id}
                className={`group rounded-xl border p-3 transition ${
                  isActive
                    ? 'border-indigo-200 bg-indigo-50'
                    : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(conversation.id)}
                  disabled={disabled}
                  className="w-full text-left disabled:cursor-not-allowed"
                >
                  <span className="block truncate text-sm font-medium text-slate-800">
                    {conversation.title}
                  </span>
                  <span className="mt-1 block text-xs text-slate-400">
                    {formatDateTime(conversation.updated_at)}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(conversation)}
                  disabled={disabled}
                  className="mt-2 text-xs text-slate-400 transition hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  删除会话
                </button>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
