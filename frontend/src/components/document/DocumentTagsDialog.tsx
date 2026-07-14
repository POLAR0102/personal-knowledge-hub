import type { KnowledgeDocument } from '../../types/document'
import type { Tag } from '../../types/tag'

interface DocumentTagsDialogProps {
  document: KnowledgeDocument
  tags: Tag[]
  updatingTagId: number | null
  error: string | null
  onAdd: (tag: Tag) => void
  onRemove: (tag: Tag) => void
  onClose: () => void
}

export function DocumentTagsDialog({
  document,
  tags,
  updatingTagId,
  error,
  onAdd,
  onRemove,
  onClose,
}: DocumentTagsDialogProps) {
  const assignedTagIds = new Set(document.tags.map((tag) => tag.id))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-tags-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium text-indigo-600">文档标签</p>
            <h2 id="document-tags-title" className="mt-1 truncate text-xl font-semibold text-slate-900">
              {document.original_filename}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={updatingTagId !== null}
            className="text-sm text-slate-400 hover:text-slate-600 disabled:opacity-50"
          >
            关闭
          </button>
        </div>

        {error && (
          <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        <div className="mt-5 space-y-2">
          {tags.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm leading-6 text-slate-400">
              暂无可用标签，请先在文档管理页创建标签。
            </p>
          ) : (
            tags.map((tag) => {
              const isAssigned = assignedTagIds.has(tag.id)
              return (
                <div
                  key={tag.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
                >
                  <span className="text-sm font-medium text-slate-700">{tag.name}</span>
                  <button
                    type="button"
                    onClick={() => (isAssigned ? onRemove(tag) : onAdd(tag))}
                    disabled={updatingTagId !== null}
                    className={`rounded-lg px-3 py-2 text-xs font-medium disabled:opacity-50 ${
                      isAssigned
                        ? 'border border-rose-200 text-rose-600 hover:bg-rose-50'
                        : 'bg-indigo-600 text-white hover:bg-indigo-500'
                    }`}
                  >
                    {updatingTagId === tag.id
                      ? '处理中…'
                      : isAssigned
                        ? '移除'
                        : '添加'}
                  </button>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
