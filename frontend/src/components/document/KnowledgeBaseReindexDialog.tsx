import { useState } from 'react'
import { reindexKnowledgeBase } from '../../api/knowledge-bases'
import type { KnowledgeBaseReindexResponse } from '../../types/knowledge-base'
import { getApiErrorMessage } from '../../utils/api-error'

interface KnowledgeBaseReindexDialogProps {
  knowledgeBaseId: number
  onClose: () => void
  onCompleted: () => void
}

export function KnowledgeBaseReindexDialog({
  knowledgeBaseId,
  onClose,
  onCompleted,
}: KnowledgeBaseReindexDialogProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<KnowledgeBaseReindexResponse | null>(null)

  async function handleReindex() {
    if (isRunning) return
    setIsRunning(true)
    setError(null)
    try {
      const response = await reindexKnowledgeBase(knowledgeBaseId)
      setResult(response)
      onCompleted()
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '知识库批量重新索引失败，请稍后重试'))
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="knowledge-base-reindex-title"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
      >
        <h2 id="knowledge-base-reindex-title" className="text-xl font-semibold text-slate-900">
          批量重新建立索引
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          只会处理解析状态为 completed 的文档。每个文档会先删除旧向量再完整重建；本阶段同步执行，不展示伪造的百分比进度。
        </p>

        {isRunning && (
          <p className="mt-5 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-700">
            正在逐个重建文档索引，请保持页面打开…
          </p>
        )}
        {error && (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-5 space-y-3">
            <p className="text-sm font-medium text-slate-700">
              共 {result.total} 个文档：成功 {result.succeeded}，失败 {result.failed}
            </p>
            {result.items.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 py-8 text-center text-sm text-slate-500">
                当前没有已完成解析的文档
              </p>
            ) : (
              result.items.map((item) => (
                <article key={item.document_id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-medium text-slate-700">
                      {item.original_filename}
                    </p>
                    <span
                      className={`shrink-0 rounded-full px-2 py-1 text-xs ${
                        item.index_status === 'indexed'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-rose-50 text-rose-700'
                      }`}
                    >
                      {item.index_status === 'indexed'
                        ? `成功 · ${item.vector_count} 个向量`
                        : '失败'}
                    </span>
                  </div>
                  {item.error_message && (
                    <p className="mt-2 text-xs text-rose-600">{item.error_message}</p>
                  )}
                </article>
              ))
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={isRunning}
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 disabled:opacity-50"
          >
            {result ? '关闭' : '取消'}
          </button>
          {!result && (
            <button
              type="button"
              disabled={isRunning}
              onClick={() => void handleReindex()}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
            >
              {isRunning ? '正在重建…' : '确认批量重建'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
