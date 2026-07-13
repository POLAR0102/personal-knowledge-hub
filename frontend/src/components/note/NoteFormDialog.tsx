import { useEffect, useState, type FormEvent } from 'react'
import type { KnowledgeBase } from '../../types/knowledge-base'
import type { Note, NoteCreate } from '../../types/note'

interface NoteFormDialogProps {
  mode: 'create' | 'edit'
  knowledgeBases: KnowledgeBase[]
  initialValue?: Note
  defaultKnowledgeBaseId?: number
  isSubmitting: boolean
  error: string | null
  onSubmit: (data: NoteCreate) => Promise<void>
  onCancel: () => void
}

export function NoteFormDialog({
  mode,
  knowledgeBases,
  initialValue,
  defaultKnowledgeBaseId,
  isSubmitting,
  error,
  onSubmit,
  onCancel,
}: NoteFormDialogProps) {
  const [knowledgeBaseId, setKnowledgeBaseId] = useState(
    initialValue?.knowledge_base_id ??
      defaultKnowledgeBaseId ??
      knowledgeBases[0]?.id ??
      0,
  )
  const [title, setTitle] = useState(initialValue?.title ?? '')
  const [content, setContent] = useState(initialValue?.content ?? '')
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    if (!knowledgeBases.some((item) => item.id === knowledgeBaseId)) {
      const preferredId = initialValue?.knowledge_base_id ?? defaultKnowledgeBaseId
      setKnowledgeBaseId(
        knowledgeBases.some((item) => item.id === preferredId)
          ? (preferredId ?? 0)
          : (knowledgeBases[0]?.id ?? 0),
      )
    }
  }, [defaultKnowledgeBaseId, initialValue?.knowledge_base_id, knowledgeBaseId, knowledgeBases])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const normalizedTitle = title.trim()
    if (!knowledgeBaseId) {
      setValidationError('请选择知识库')
      return
    }
    if (!normalizedTitle) {
      setValidationError('请输入笔记标题')
      return
    }
    if (!content.trim()) {
      setValidationError('请输入笔记内容')
      return
    }
    if (content.length > 100_000) {
      setValidationError('笔记内容不能超过 100000 个字符')
      return
    }

    setValidationError(null)
    await onSubmit({
      knowledge_base_id: knowledgeBaseId,
      title: normalizedTitle,
      content,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="note-form-title"
        className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
      >
        <p className="text-xs font-medium text-indigo-600">Markdown 笔记</p>
        <h2 id="note-form-title" className="mt-1 text-xl font-semibold text-slate-900">
          {mode === 'create' ? '创建笔记' : '编辑笔记'}
        </h2>

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            知识库
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(Number(event.target.value))}
              disabled={isSubmitting || mode === 'edit'}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
            >
              {knowledgeBases.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            标题
            <input
              autoFocus
              required
              maxLength={100}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={isSubmitting}
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
              placeholder="例如：RAG 学习笔记"
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {title.length}/100
            </span>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            内容（支持 Markdown）
            <textarea
              rows={14}
              maxLength={100_000}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              disabled={isSubmitting}
              className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 font-mono text-sm leading-6 outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
              placeholder={'## 标题\n\n在这里记录内容…'}
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {content.length}/100000
            </span>
          </label>

          {knowledgeBases.length === 0 && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              请先创建知识库，再创建笔记。
            </p>
          )}
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
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              {isSubmitting ? '正在保存…' : '保存笔记'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
