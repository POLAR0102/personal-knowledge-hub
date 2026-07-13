import ReactMarkdown from 'react-markdown'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content?: string
  isLoading?: boolean
}

export function ChatMessage({ role, content, isLoading }: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <article className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
          AI
        </span>
      )}
      <div
        className={`max-w-3xl rounded-2xl px-4 py-3 text-sm leading-7 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'border border-slate-200 bg-slate-50 text-slate-700'
        }`}
      >
        <p className={`mb-1 text-xs font-semibold ${isUser ? 'text-indigo-100' : 'text-slate-400'}`}>
          {isUser ? '你' : '知识库助手'}
        </p>
        {isLoading ? (
          <p className="animate-pulse text-slate-500">正在查找相关资料并生成回答…</p>
        ) : isUser ? (
          <p className="whitespace-pre-wrap break-words">{content}</p>
        ) : (
          <div className="break-words [&_ol]:list-decimal [&_ol]:pl-5 [&_p+p]:mt-3 [&_ul]:list-disc [&_ul]:pl-5">
            <ReactMarkdown>{content ?? ''}</ReactMarkdown>
          </div>
        )}
      </div>
    </article>
  )
}
