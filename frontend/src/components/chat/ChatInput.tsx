import type { FormEvent, KeyboardEvent } from 'react'

interface ChatInputProps {
  question: string
  topK: number
  isSubmitting: boolean
  disabled: boolean
  onQuestionChange: (question: string) => void
  onTopKChange: (topK: number) => void
  onSubmit: () => void
}

export function ChatInput({
  question,
  topK,
  isSubmitting,
  disabled,
  onQuestionChange,
  onTopKChange,
  onSubmit,
}: ChatInputProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      if (!disabled && !isSubmitting && question.trim()) {
        onSubmit()
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-[1fr_9rem]">
        <label className="block text-sm font-medium text-slate-700">
          你的问题
          <textarea
            rows={4}
            maxLength={1000}
            value={question}
            disabled={disabled || isSubmitting}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="例如：请总结项目使用的技术栈和开发周期"
            className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm leading-6 outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          />
          <span className="mt-1 flex justify-between text-xs text-slate-400">
            <span>Enter 发送，Shift + Enter 换行</span>
            <span>{question.length} / 1000</span>
          </span>
        </label>

        <label className="block text-sm font-medium text-slate-700">
          检索片段数
          <input
            type="number"
            min={1}
            max={10}
            value={topK}
            disabled={disabled || isSubmitting}
            onChange={(event) => onTopKChange(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          />
        </label>
      </div>

      <button
        type="submit"
        disabled={disabled || isSubmitting || !question.trim()}
        className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? '正在检索知识并生成回答…' : '发送问题'}
      </button>
    </form>
  )
}
