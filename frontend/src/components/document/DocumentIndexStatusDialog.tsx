import { useCallback, useEffect, useState } from 'react'
import { getDocumentIndexStatus } from '../../api/documents'
import type {
  DocumentIndexStatusResponse,
  KnowledgeDocument,
} from '../../types/document'
import { getApiErrorMessage } from '../../utils/api-error'
import { formatDateTime } from '../../utils/date'

interface DocumentIndexStatusDialogProps {
  document: KnowledgeDocument
  onClose: () => void
}

export function DocumentIndexStatusDialog({
  document,
  onClose,
}: DocumentIndexStatusDialogProps) {
  const [status, setStatus] = useState<DocumentIndexStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setStatus(await getDocumentIndexStatus(document.id))
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '索引状态加载失败，请稍后重试'))
    } finally {
      setIsLoading(false)
    }
  }, [document.id])

  useEffect(() => {
    void loadStatus()
  }, [loadStatus])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-index-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium text-violet-600">向量索引详情</p>
            <h2 id="document-index-title" className="mt-1 truncate text-xl font-semibold text-slate-900">
              {document.original_filename}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            关闭
          </button>
        </div>

        {isLoading ? (
          <p className="py-12 text-center text-sm text-slate-500">正在读取索引状态…</p>
        ) : error ? (
          <div className="mt-6 rounded-xl bg-rose-50 p-5 text-center text-sm text-rose-700">
            <p>{error}</p>
            <button type="button" onClick={() => void loadStatus()} className="mt-3 underline">
              重新加载
            </button>
          </div>
        ) : status ? (
          <dl className="mt-6 grid gap-4 rounded-xl bg-slate-50 p-5 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-400">解析状态</dt>
              <dd className="mt-1 font-medium text-slate-700">{status.processing_status}</dd>
            </div>
            <div>
              <dt className="text-slate-400">索引状态</dt>
              <dd className="mt-1 font-medium text-slate-700">{status.index_status}</dd>
            </div>
            <div>
              <dt className="text-slate-400">文本片段数</dt>
              <dd className="mt-1 font-medium text-slate-700">{status.chunk_count}</dd>
            </div>
            <div>
              <dt className="text-slate-400">向量数</dt>
              <dd className="mt-1 font-medium text-slate-700">{status.vector_count}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-slate-400">Embedding 模型</dt>
              <dd className="mt-1 break-all font-medium text-slate-700">
                {status.embedding_model || '尚未记录'}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-slate-400">索引时间</dt>
              <dd className="mt-1 font-medium text-slate-700">
                {status.indexed_at ? formatDateTime(status.indexed_at) : '尚未完成索引'}
              </dd>
            </div>
            {status.index_error_message && (
              <div className="sm:col-span-2">
                <dt className="text-rose-500">失败原因</dt>
                <dd className="mt-1 text-rose-700">{status.index_error_message}</dd>
              </div>
            )}
          </dl>
        ) : null}
      </div>
    </div>
  )
}
