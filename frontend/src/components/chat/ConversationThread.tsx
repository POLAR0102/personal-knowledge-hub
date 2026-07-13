import type { ConversationMessage } from '../../types/conversation'
import { ChatMessage } from './ChatMessage'
import { CitationList } from './CitationList'

interface ConversationThreadProps {
  messages: ConversationMessage[]
  isSubmitting: boolean
  pendingContent: string | null
  pendingRequestId: string | null
  onRetry: (message: ConversationMessage) => void
}

export function ConversationThread({
  messages,
  isSubmitting,
  pendingContent,
  pendingRequestId,
  onRetry,
}: ConversationThreadProps) {
  if (messages.length === 0 && !pendingContent) {
    return (
      <div className="flex min-h-80 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center">
        <div>
          <p className="font-medium text-slate-700">这个会话还没有消息</p>
          <p className="mt-2 text-sm text-slate-400">在下方输入问题，回答会连同真实引用一起保存。</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {messages.map((message) => (
        <div key={message.id} className="space-y-3">
          <ChatMessage role={message.role} content={message.content} />
          {message.role === 'assistant' && (
            <div className="ml-0 space-y-3 sm:ml-12">
              <CitationList citations={message.citations ?? []} />
              {message.model && (
                <p className="text-xs text-slate-400">模型：{message.model}</p>
              )}
            </div>
          )}
          {message.role === 'user' &&
            message.request_status === 'failed' &&
            message.client_request_id !== pendingRequestId && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => onRetry(message)}
                disabled={isSubmitting || !message.client_request_id}
                className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                上次生成失败，重新尝试
              </button>
            </div>
          )}
          {message.role === 'user' && message.request_status === 'processing' && (
            <p className="text-right text-xs text-amber-600">这条问题正在处理中…</p>
          )}
          {message.role === 'user' &&
            message.client_request_id === pendingRequestId &&
            !messages.some(
              (candidate) =>
                candidate.role === 'assistant' &&
                candidate.sequence_number === message.sequence_number + 1,
            ) && (
              <ChatMessage role="assistant" isLoading />
            )}
        </div>
      ))}

      {pendingContent && !messages.some(
        (message) => message.client_request_id === pendingRequestId,
      ) && (
        <div className="space-y-5">
          <ChatMessage role="user" content={pendingContent} />
          <ChatMessage role="assistant" isLoading />
        </div>
      )}
    </div>
  )
}
