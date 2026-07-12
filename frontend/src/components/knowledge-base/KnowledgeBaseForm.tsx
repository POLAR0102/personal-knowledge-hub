import { useState, type FormEvent } from 'react'
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
} from '../../types/knowledge-base'

interface KnowledgeBaseFormProps {
  mode: 'create' | 'edit'
  initialValue?: KnowledgeBase
  isSubmitting: boolean
  error: string | null
  onSubmit: (data: KnowledgeBaseCreate) => Promise<void>
  onCancel: () => void
}

export function KnowledgeBaseForm({
  mode,
  initialValue,
  isSubmitting,
  error,
  onSubmit,
  onCancel,
}: KnowledgeBaseFormProps) {
  const [name, setName] = useState(initialValue?.name ?? '')
  const [description, setDescription] = useState(
    initialValue?.description ?? '',
  )
  const [validationError, setValidationError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const normalizedName = name.trim()
    const normalizedDescription = description.trim()
    if (!normalizedName) {
      setValidationError('请输入知识库名称')
      return
    }
    if (normalizedName.length > 100) {
      setValidationError('知识库名称不能超过 100 个字符')
      return
    }
    if (description.length > 500) {
      setValidationError('描述不能超过 500 个字符')
      return
    }

    setValidationError(null)
    await onSubmit({
      name: normalizedName,
      description: normalizedDescription || null,
    })
  }

  const title = mode === 'create' ? '创建知识库' : '编辑知识库'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="knowledge-base-form-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div>
          <p className="text-xs font-medium text-indigo-600">知识库管理</p>
          <h2
            id="knowledge-base-form-title"
            className="mt-1 text-xl font-semibold text-slate-900"
          >
            {title}
          </h2>
        </div>

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">名称</span>
            <input
              autoFocus
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={isSubmitting}
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
              placeholder="例如：毕业设计资料"
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {name.length}/100
            </span>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">描述（可选）</span>
            <textarea
              rows={5}
              maxLength={500}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
              placeholder="简单说明这个知识库的用途"
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {description.length}/500
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
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? '正在保存…' : mode === 'create' ? '创建' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
