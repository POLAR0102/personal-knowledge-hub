import { useState, type FormEvent } from 'react'
import type { ConversationCreate } from '../../types/conversation'
import type { KnowledgeBase } from '../../types/knowledge-base'

interface NewConversationDialogProps {
  knowledgeBases: KnowledgeBase[]
  isSubmitting: boolean
  error: string | null
  onSubmit: (data: ConversationCreate) => Promise<void>
  onCancel: () => void
}

export function NewConversationDialog({
  knowledgeBases,
  isSubmitting,
  error,
  onSubmit,
  onCancel,
}: NewConversationDialogProps) {
  const [knowledgeBaseId, setKnowledgeBaseId] = useState(
    knowledgeBases[0]?.id ?? 0,
  )
  const [title, setTitle] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const normalizedTitle = title.trim()
    if (!knowledgeBaseId) {
      setValidationError('请选择知识库')
      return
    }
    if (!normalizedTitle) {
      setValidationError('请输入会话标题')
      return
    }
    if (normalizedTitle.length > 100) {
      setValidationError('会话标题不能超过 100 个字符')
      return
    }

    setValidationError(null)
    await onSubmit({ knowledge_base_id: knowledgeBaseId, title: normalizedTitle })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-conversation-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <p className="text-xs font-medium text-indigo-600">阶段 E · 会话历史</p>
        <h2 id="new-conversation-title" className="mt-1 text-xl font-semibold text-slate-900">
          新建问答会话
        </h2>

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            知识库
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(Number(event.target.value))}
              disabled={isSubmitting}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
            >
              {knowledgeBases.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.name}
                </option>
              ))}
            </select>
            {knowledgeBases.length === 0 && (
              <span className="mt-2 block text-xs text-amber-600">
                请先创建知识库，再新建问答会话。
              </span>
            )}
          </label>

          <label className="block text-sm font-medium text-slate-700">
            会话标题
            <input
              autoFocus
              required
              maxLength={100}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={isSubmitting}
              placeholder="例如：毕业设计问答"
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {title.length}/100
            </span>
          </label>

          {(validationError || error) && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {validationError || error}
            </p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting || knowledgeBases.length === 0}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? '正在创建…' : '创建会话'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
