import type { KnowledgeDocument } from '../../types/document'
import { formatDateTime } from '../../utils/date'
import { formatFileSize } from '../../utils/file'

const statusView = {
  pending: { label: '等待处理', className: 'bg-amber-50 text-amber-700' },
  processing: { label: '处理中', className: 'bg-blue-50 text-blue-700' },
  completed: { label: '处理完成', className: 'bg-emerald-50 text-emerald-700' },
  failed: { label: '处理失败', className: 'bg-rose-50 text-rose-700' },
}

interface DocumentListProps {
  items: KnowledgeDocument[]
  onDelete: (document: KnowledgeDocument) => void
  onProcess: (document: KnowledgeDocument) => void
  onViewChunks: (document: KnowledgeDocument) => void
  processingDocumentId: number | null
}

export function DocumentList({
  items,
  onDelete,
  onProcess,
  onViewChunks,
  processingDocumentId,
}: DocumentListProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="divide-y divide-slate-100">
        {items.map((document) => {
          const status = statusView[document.status]
          return (
            <article
              key={document.id}
              className="flex flex-col gap-4 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-medium text-slate-800">
                    {document.original_filename}
                  </p>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${status.className}`}>
                    {status.label}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {document.file_type.toUpperCase()} · {formatFileSize(document.file_size)} · 上传于{' '}
                  {formatDateTime(document.created_at)}
                </p>
                {document.error_message && (
                  <p className="mt-2 text-xs text-rose-600">{document.error_message}</p>
                )}
                {document.status === 'completed' && (
                  <p className="mt-2 text-xs font-medium text-emerald-700">
                    已生成 {document.chunk_count} 个文本片段
                  </p>
                )}
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {(document.status === 'pending' || document.status === 'failed') && (
                  <button
                    type="button"
                    disabled={processingDocumentId !== null}
                    onClick={() => onProcess(document)}
                    className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {processingDocumentId === document.id
                      ? '正在处理…'
                      : document.status === 'failed'
                        ? '重新处理'
                        : '开始处理'}
                  </button>
                )}
                {document.status === 'processing' && (
                  <button
                    type="button"
                    disabled
                    className="rounded-lg bg-blue-50 px-3 py-2 text-xs font-medium text-blue-600 opacity-70"
                  >
                    正在处理…
                  </button>
                )}
                {document.status === 'completed' && (
                  <button
                    type="button"
                    onClick={() => onViewChunks(document)}
                    className="rounded-lg border border-indigo-200 px-3 py-2 text-xs font-medium text-indigo-600 transition hover:bg-indigo-50"
                  >
                    查看文本片段
                  </button>
                )}
                <button
                  type="button"
                  disabled={processingDocumentId === document.id || document.status === 'processing'}
                  onClick={() => onDelete(document)}
                  className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  删除
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
