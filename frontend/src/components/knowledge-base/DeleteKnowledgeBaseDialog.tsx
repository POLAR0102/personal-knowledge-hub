import type { KnowledgeBase } from '../../types/knowledge-base'

interface DeleteKnowledgeBaseDialogProps {
  knowledgeBase: KnowledgeBase
  isDeleting: boolean
  error: string | null
  onConfirm: () => void
  onCancel: () => void
}

export function DeleteKnowledgeBaseDialog({
  knowledgeBase,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: DeleteKnowledgeBaseDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-knowledge-base-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <h2
          id="delete-knowledge-base-title"
          className="text-xl font-semibold text-slate-900"
        >
          删除知识库？
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          你将删除“{knowledgeBase.name}”。此操作无法撤销，请确认后再继续。
        </p>
        {error && (
          <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeleting ? '正在删除…' : '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )
}
