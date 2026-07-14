import { useState, type FormEvent } from 'react'
import { createTag, deleteTag, updateTag } from '../../api/tags'
import type { Tag } from '../../types/tag'
import { getApiErrorMessage } from '../../utils/api-error'

interface TagManagerDialogProps {
  tags: Tag[]
  onChange: (tags: Tag[]) => void
  onClose: () => void
}

export function TagManagerDialog({
  tags,
  onChange,
  onClose,
}: TagManagerDialogProps) {
  const [name, setName] = useState('')
  const [editingTag, setEditingTag] = useState<Tag | null>(null)
  const [editingName, setEditingName] = useState('')
  const [deletingTag, setDeletingTag] = useState<Tag | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function validateName(value: string): string | null {
    const normalized = value.trim()
    if (!normalized) return '请输入标签名称'
    if (normalized.length > 30) return '标签名称不能超过 30 个字符'
    return null
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    const validationError = validateName(name)
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const created = await createTag({ name: name.trim() })
      onChange([created, ...tags])
      setName('')
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '标签创建失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleUpdate() {
    if (!editingTag || isSubmitting) return
    const validationError = validateName(editingName)
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const updated = await updateTag(editingTag.id, {
        name: editingName.trim(),
      })
      onChange(tags.map((tag) => (tag.id === updated.id ? updated : tag)))
      setEditingTag(null)
      setEditingName('')
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '标签修改失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!deletingTag || isSubmitting) return
    setIsSubmitting(true)
    setError(null)
    try {
      await deleteTag(deletingTag.id)
      onChange(tags.filter((tag) => tag.id !== deletingTag.id))
      setDeletingTag(null)
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '标签删除失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tag-manager-title"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium text-indigo-600">文档整理</p>
            <h2 id="tag-manager-title" className="mt-1 text-xl font-semibold text-slate-900">
              标签管理
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="text-sm text-slate-400 hover:text-slate-600 disabled:opacity-50"
          >
            关闭
          </button>
        </div>

        <form onSubmit={handleCreate} className="mt-6 flex gap-2">
          <input
            value={name}
            maxLength={30}
            disabled={isSubmitting}
            onChange={(event) => setName(event.target.value)}
            placeholder="新标签名称"
            className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
          <button
            type="submit"
            disabled={isSubmitting || !name.trim()}
            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            创建
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        <div className="mt-5 space-y-2">
          {tags.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-400">
              还没有标签
            </p>
          ) : (
            tags.map((tag) => (
              <div
                key={tag.id}
                className="rounded-xl border border-slate-100 bg-slate-50 p-3"
              >
                {editingTag?.id === tag.id ? (
                  <div className="flex gap-2">
                    <input
                      autoFocus
                      maxLength={30}
                      value={editingName}
                      disabled={isSubmitting}
                      onChange={(event) => setEditingName(event.target.value)}
                      className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
                    />
                    <button
                      type="button"
                      onClick={() => void handleUpdate()}
                      disabled={isSubmitting}
                      className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                    >
                      保存
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingTag(null)}
                      disabled={isSubmitting}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600"
                    >
                      取消
                    </button>
                  </div>
                ) : deletingTag?.id === tag.id ? (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-rose-700">
                      确认删除“{tag.name}”？文档上的该标签会一并移除。
                    </p>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void handleDelete()}
                        disabled={isSubmitting}
                        className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                      >
                        确认删除
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeletingTag(null)}
                        disabled={isSubmitting}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-3">
                    <span className="rounded-full bg-white px-3 py-1 text-sm font-medium text-slate-700">
                      {tag.name}
                    </span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setError(null)
                          setEditingTag(tag)
                          setEditingName(tag.name)
                        }}
                        className="text-xs font-medium text-indigo-600"
                      >
                        重命名
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setError(null)
                          setDeletingTag(tag)
                        }}
                        className="text-xs font-medium text-rose-600"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
