import { useCallback, useEffect, useState } from 'react'
import { listDocumentChunks } from '../../api/documents'
import type { DocumentChunk, KnowledgeDocument } from '../../types/document'
import { getApiErrorMessage } from '../../utils/api-error'

const PAGE_SIZE = 5

interface DocumentChunksDialogProps {
  document: KnowledgeDocument
  onClose: () => void
}

export function DocumentChunksDialog({
  document,
  onClose,
}: DocumentChunksDialogProps) {
  const [items, setItems] = useState<DocumentChunk[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadItems = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await listDocumentChunks(document.id, {
        page,
        page_size: PAGE_SIZE,
      })
      setItems(data.items)
      setTotal(data.total)
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '文本片段加载失败，请稍后重试'))
    } finally {
      setIsLoading(false)
    }
  }, [document.id, page])

  useEffect(() => {
    void loadItems()
  }, [loadItems])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-chunks-title"
        className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-6">
          <div className="min-w-0">
            <p className="text-xs font-medium text-indigo-600">文本片段调试</p>
            <h2 id="document-chunks-title" className="mt-1 truncate text-xl font-semibold text-slate-900">
              {document.original_filename}
            </h2>
            <p className="mt-1 text-xs text-slate-400">共 {total} 个 Chunk，按原文顺序展示</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            关闭
          </button>
        </div>

        <div className="overflow-y-auto p-6">
          {isLoading ? (
            <p className="py-12 text-center text-sm text-slate-500">正在加载文本片段…</p>
          ) : error ? (
            <div className="rounded-xl bg-rose-50 p-5 text-center text-sm text-rose-700">
              <p>{error}</p>
              <button type="button" onClick={() => void loadItems()} className="mt-3 underline">
                重新加载
              </button>
            </div>
          ) : items.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 py-12 text-center text-sm text-slate-500">
              当前没有文本片段
            </p>
          ) : (
            <div className="space-y-4">
              {items.map((chunk) => (
                <article key={chunk.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="rounded-full bg-indigo-50 px-2 py-1 font-medium text-indigo-700">
                      Chunk #{chunk.chunk_index}
                    </span>
                    <span>{chunk.character_count} 字符</span>
                    {chunk.page_number && <span>第 {chunk.page_number} 页</span>}
                    {chunk.section_title && <span>章节：{chunk.section_title}</span>}
                  </div>
                  <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-700">
                    {chunk.content}
                  </pre>
                </article>
              ))}
            </div>
          )}
        </div>

        {!isLoading && !error && total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-slate-100 px-6 py-4 text-sm">
            <span className="text-slate-500">第 {page} / {totalPages} 页</span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
