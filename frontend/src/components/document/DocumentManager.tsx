import { useCallback, useEffect, useState } from 'react'
import {
  deleteDocument,
  indexDocument,
  listDocuments,
  processDocument,
  uploadDocument,
} from '../../api/documents'
import type { KnowledgeDocument } from '../../types/document'
import { getApiErrorMessage } from '../../utils/api-error'
import { DeleteDocumentDialog } from './DeleteDocumentDialog'
import { DocumentChunksDialog } from './DocumentChunksDialog'
import { DocumentList } from './DocumentList'
import { DocumentIndexStatusDialog } from './DocumentIndexStatusDialog'
import { DocumentUploader } from './DocumentUploader'
import { KnowledgeBaseReindexDialog } from './KnowledgeBaseReindexDialog'

const PAGE_SIZE = 10

interface DocumentManagerProps {
  knowledgeBaseId: number
}

export function DocumentManager({ knowledgeBaseId }: DocumentManagerProps) {
  const [items, setItems] = useState<KnowledgeDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [deletingDocument, setDeletingDocument] = useState<KnowledgeDocument | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null)
  const [processError, setProcessError] = useState<string | null>(null)
  const [indexingDocumentId, setIndexingDocumentId] = useState<number | null>(null)
  const [indexError, setIndexError] = useState<string | null>(null)
  const [viewingDocument, setViewingDocument] = useState<KnowledgeDocument | null>(null)
  const [viewingIndexDocument, setViewingIndexDocument] = useState<KnowledgeDocument | null>(null)
  const [isReindexDialogOpen, setIsReindexDialogOpen] = useState(false)

  const loadItems = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await listDocuments(knowledgeBaseId, {
        page,
        page_size: PAGE_SIZE,
      })
      setItems(data.items)
      setTotal(data.total)
    } catch (error: unknown) {
      setLoadError(getApiErrorMessage(error, '文档列表加载失败，请稍后重试'))
    } finally {
      setIsLoading(false)
    }
  }, [knowledgeBaseId, page])

  useEffect(() => {
    void loadItems()
  }, [loadItems])

  async function handleUpload(file: File) {
    if (isUploading) return
    setIsUploading(true)
    setUploadProgress(0)
    setUploadError(null)
    try {
      await uploadDocument(knowledgeBaseId, file, (event) => {
        if (event.total) {
          setUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
        }
      })
      setUploadProgress(100)
      if (page !== 1) {
        setPage(1)
      } else {
        await loadItems()
      }
    } catch (error: unknown) {
      setUploadError(getApiErrorMessage(error, '文档上传失败，请稍后重试'))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDelete() {
    if (!deletingDocument || isDeleting) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteDocument(deletingDocument.id)
      setDeletingDocument(null)
      if (items.length === 1 && page > 1) {
        setPage((current) => current - 1)
      } else {
        await loadItems()
      }
    } catch (error: unknown) {
      setDeleteError(getApiErrorMessage(error, '文档删除失败，请稍后重试'))
    } finally {
      setIsDeleting(false)
    }
  }

  async function handleProcess(document: KnowledgeDocument) {
    if (processingDocumentId !== null) return
    setProcessingDocumentId(document.id)
    setProcessError(null)
    try {
      await processDocument(document.id)
    } catch (error: unknown) {
      setProcessError(getApiErrorMessage(error, '文档处理失败，请稍后重试'))
    } finally {
      await loadItems()
      setProcessingDocumentId(null)
    }
  }

  async function handleIndex(document: KnowledgeDocument) {
    if (indexingDocumentId !== null) return
    setIndexingDocumentId(document.id)
    setIndexError(null)
    try {
      await indexDocument(document.id)
    } catch (error: unknown) {
      setIndexError(getApiErrorMessage(error, '文档索引失败，请稍后重试'))
    } finally {
      await loadItems()
      setIndexingDocumentId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-slate-900">知识库文档</p>
          <p className="mt-1 text-sm text-slate-500">
            上传资料并管理处理状态，当前共 {total} 个文档
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-fit rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
            上传后等待解析
          </span>
          <button
            type="button"
            disabled={total === 0 || isLoading}
            onClick={() => setIsReindexDialogOpen(true)}
            className="rounded-lg border border-violet-200 px-3 py-2 text-xs font-medium text-violet-700 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            批量重新索引
          </button>
        </div>
      </div>

      <div className="mt-6">
        <DocumentUploader
          isUploading={isUploading}
          progress={uploadProgress}
          error={uploadError}
          onUpload={handleUpload}
        />
      </div>

      <div className="mt-8">
        {processError && (
          <p className="mb-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {processError}
          </p>
        )}
        {indexError && (
          <p className="mb-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {indexError}
          </p>
        )}
        {isLoading ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
            正在加载文档…
          </div>
        ) : loadError ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-6 py-8 text-center">
            <p className="text-sm text-rose-700">{loadError}</p>
            <button
              type="button"
              onClick={() => void loadItems()}
              className="mt-3 rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm text-rose-700"
            >
              重新加载
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            <p className="text-sm font-medium text-slate-700">还没有文档</p>
            <p className="mt-1 text-xs text-slate-400">选择或拖拽文件到上方区域开始上传</p>
          </div>
        ) : (
          <>
            <DocumentList
              items={items}
              processingDocumentId={processingDocumentId}
              indexingDocumentId={indexingDocumentId}
              onProcess={(document) => void handleProcess(document)}
              onIndex={(document) => void handleIndex(document)}
              onViewIndexStatus={setViewingIndexDocument}
              onViewChunks={setViewingDocument}
              onDelete={(document) => {
                setDeleteError(null)
                setDeletingDocument(document)
              }}
            />
            <nav
              aria-label="文档分页"
              className="mt-4 flex items-center justify-between text-sm"
            >
              <span className="text-slate-500">
                第 {page} / {totalPages} 页
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => current - 1)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  上一页
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((current) => current + 1)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  下一页
                </button>
              </div>
            </nav>
          </>
        )}
      </div>

      {deletingDocument && (
        <DeleteDocumentDialog
          document={deletingDocument}
          isDeleting={isDeleting}
          error={deleteError}
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            setDeletingDocument(null)
            setDeleteError(null)
          }}
        />
      )}

      {viewingDocument && (
        <DocumentChunksDialog
          document={viewingDocument}
          onClose={() => setViewingDocument(null)}
        />
      )}

      {viewingIndexDocument && (
        <DocumentIndexStatusDialog
          document={viewingIndexDocument}
          onClose={() => setViewingIndexDocument(null)}
        />
      )}

      {isReindexDialogOpen && (
        <KnowledgeBaseReindexDialog
          knowledgeBaseId={knowledgeBaseId}
          onCompleted={() => void loadItems()}
          onClose={() => setIsReindexDialogOpen(false)}
        />
      )}
    </section>
  )
}
