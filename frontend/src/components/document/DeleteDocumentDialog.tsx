import type { KnowledgeDocument } from '../../types/document'

interface DeleteDocumentDialogProps {
  document: KnowledgeDocument
  isDeleting: boolean
  error: string | null
  onConfirm: () => void
  onCancel: () => void
}

export function DeleteDocumentDialog({
  document,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: DeleteDocumentDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-document-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <h2 id="delete-document-title" className="text-xl font-semibold text-slate-900">
          删除文档？
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          你将删除“{document.original_filename}”，数据库记录和磁盘文件都会被清理。
        </p>
        {error && (
          <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
          >
            取消
          </button>
          <button
            type="button"
            disabled={isDeleting}
            onClick={onConfirm}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500 disabled:opacity-60"
          >
            {isDeleting ? '正在删除…' : '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )
}
