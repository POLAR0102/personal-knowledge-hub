import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addDocumentTag,
  listAllDocuments,
  listFavoriteDocuments,
  removeDocumentTag,
  setDocumentFavorite,
} from '../../api/documents'
import { listKnowledgeBases } from '../../api/knowledge-bases'
import { listTags } from '../../api/tags'
import type {
  DocumentLibraryParams,
} from '../../api/documents'
import type { DocumentStatus, KnowledgeDocument } from '../../types/document'
import type { KnowledgeBase } from '../../types/knowledge-base'
import type { Tag } from '../../types/tag'
import { getApiErrorMessage } from '../../utils/api-error'
import { DocumentCatalog } from './DocumentCatalog'
import {
  DocumentLibraryFilters,
  type FavoriteFilter,
} from './DocumentLibraryFilters'
import { DocumentTagsDialog } from './DocumentTagsDialog'
import { TagManagerDialog } from './TagManagerDialog'

const PAGE_SIZE = 10

interface DocumentLibraryProps {
  favoritesOnly?: boolean
}

export function DocumentLibrary({ favoritesOnly = false }: DocumentLibraryProps) {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [resourceError, setResourceError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [filenameInput, setFilenameInput] = useState('')
  const [filename, setFilename] = useState('')
  const [status, setStatus] = useState<DocumentStatus | null>(null)
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<number | null>(null)
  const [tagId, setTagId] = useState<number | null>(null)
  const [favorite, setFavorite] = useState<FavoriteFilter>('all')
  const [updatingFavoriteId, setUpdatingFavoriteId] = useState<number | null>(null)
  const [taggedDocument, setTaggedDocument] = useState<KnowledgeDocument | null>(null)
  const [updatingTagId, setUpdatingTagId] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isTagManagerOpen, setIsTagManagerOpen] = useState(false)
  const documentRequestId = useRef(0)

  useEffect(() => {
    let cancelled = false
    setResourceError(null)
    void Promise.allSettled([
      listKnowledgeBases({ page: 1, page_size: 100 }),
      listTags({ page: 1, page_size: 100 }),
    ]).then(([knowledgeBaseResult, tagResult]) => {
      if (cancelled) return
      if (knowledgeBaseResult.status === 'fulfilled') {
        setKnowledgeBases(knowledgeBaseResult.value.items)
      }
      if (tagResult.status === 'fulfilled') {
        setTags(tagResult.value.items)
      }
      if (
        knowledgeBaseResult.status === 'rejected' ||
        tagResult.status === 'rejected'
      ) {
        setResourceError('知识库或标签加载失败，部分筛选暂不可用')
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  const loadDocuments = useCallback(async () => {
    const requestId = documentRequestId.current + 1
    documentRequestId.current = requestId
    setIsLoading(true)
    setLoadError(null)
    const params: DocumentLibraryParams = {
      page,
      page_size: PAGE_SIZE,
      ...(filename && { filename }),
      ...(status && { status }),
      ...(knowledgeBaseId !== null && { knowledge_base_id: knowledgeBaseId }),
      ...(tagId !== null && { tag_id: tagId }),
      ...(!favoritesOnly &&
        favorite !== 'all' && {
          is_favorite: favorite === 'favorite',
        }),
    }

    try {
      const data = favoritesOnly
        ? await listFavoriteDocuments(params)
        : await listAllDocuments(params)
      if (requestId !== documentRequestId.current) return
      setDocuments(data.items)
      setTotal(data.total)
    } catch (error: unknown) {
      if (requestId !== documentRequestId.current) return
      setLoadError(getApiErrorMessage(error, '文档列表加载失败，请稍后重试'))
    } finally {
      if (requestId === documentRequestId.current) {
        setIsLoading(false)
      }
    }
  }, [favorite, favoritesOnly, filename, knowledgeBaseId, page, status, tagId])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  function replaceDocument(updated: KnowledgeDocument) {
    setDocuments((current) =>
      current.map((document) =>
        document.id === updated.id ? updated : document,
      ),
    )
    setTaggedDocument((current) =>
      current?.id === updated.id ? updated : current,
    )
  }

  async function handleToggleFavorite(document: KnowledgeDocument) {
    if (updatingFavoriteId !== null) return
    setUpdatingFavoriteId(document.id)
    setActionError(null)
    try {
      const updated = await setDocumentFavorite(
        document.id,
        !document.is_favorite,
      )
      const leavesCurrentList =
        favoritesOnly ||
        (favorite === 'favorite' && !updated.is_favorite) ||
        (favorite === 'not_favorite' && updated.is_favorite)
      if (leavesCurrentList) {
        if (documents.length === 1 && page > 1) {
          setPage((current) => current - 1)
        } else {
          await loadDocuments()
        }
      } else {
        replaceDocument(updated)
      }
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '文档收藏状态修改失败'))
    } finally {
      setUpdatingFavoriteId(null)
    }
  }

  async function handleAddTag(tag: Tag) {
    if (!taggedDocument || updatingTagId !== null) return
    setUpdatingTagId(tag.id)
    setActionError(null)
    try {
      replaceDocument(await addDocumentTag(taggedDocument.id, tag.id))
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '文档标签添加失败'))
    } finally {
      setUpdatingTagId(null)
    }
  }

  async function handleRemoveTag(tag: Tag) {
    if (!taggedDocument || updatingTagId !== null) return
    setUpdatingTagId(tag.id)
    setActionError(null)
    try {
      const documentId = taggedDocument.id
      await removeDocumentTag(documentId, tag.id)
      const updated = {
        ...taggedDocument,
        tags: taggedDocument.tags.filter((item) => item.id !== tag.id),
      }
      if (tagId === tag.id) {
        setTaggedDocument(null)
        if (documents.length === 1 && page > 1) {
          setPage((current) => current - 1)
        } else {
          await loadDocuments()
        }
      } else {
        replaceDocument(updated)
      }
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '文档标签移除失败'))
    } finally {
      setUpdatingTagId(null)
    }
  }

  function resetFilters() {
    setFilenameInput('')
    setFilename('')
    setStatus(null)
    setKnowledgeBaseId(null)
    setTagId(null)
    setFavorite('all')
    setPage(1)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const isOrganizing =
    updatingFavoriteId !== null || updatingTagId !== null
  const isFiltering =
    Boolean(filename) ||
    status !== null ||
    knowledgeBaseId !== null ||
    tagId !== null ||
    (!favoritesOnly && favorite !== 'all')

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-5 rounded-2xl bg-gradient-to-r from-slate-950 to-cyan-950 p-6 text-white shadow-sm sm:p-8 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-cyan-300">阶段 G · 文档整理</p>
          <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">
            {favoritesOnly ? '收藏文档' : '文档资料库'}
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
            {favoritesOnly
              ? '集中查看已收藏的重点资料，并继续使用知识库与标签筛选。'
              : '跨知识库搜索文件，通过标签和收藏整理个人资料。'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {favoritesOnly ? (
            <Link
              to="/documents"
              className="rounded-xl border border-white/20 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
            >
              查看全部文档
            </Link>
          ) : (
            <Link
              to="/favorites"
              className="rounded-xl border border-amber-300/40 bg-amber-300/10 px-4 py-2.5 text-sm font-semibold text-amber-100 hover:bg-amber-300/20"
            >
              ★ 我的收藏
            </Link>
          )}
          <Link
            to="/knowledge-bases"
            className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-100"
          >
            上传文档
          </Link>
          <Link
            to="/semantic-search"
            className="rounded-xl border border-white/20 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
          >
            语义检索
          </Link>
        </div>
      </section>

      {resourceError && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {resourceError}
        </p>
      )}

      <DocumentLibraryFilters
        filenameInput={filenameInput}
        status={status}
        knowledgeBaseId={knowledgeBaseId}
        tagId={tagId}
        favorite={favorite}
        favoritesOnly={favoritesOnly}
        knowledgeBases={knowledgeBases}
        tags={tags}
        disabled={isLoading || isOrganizing}
        onFilenameInputChange={setFilenameInput}
        onSearch={() => {
          setFilename(filenameInput.trim())
          setPage(1)
        }}
        onStatusChange={(value) => {
          setStatus(value)
          setPage(1)
        }}
        onKnowledgeBaseChange={(value) => {
          setKnowledgeBaseId(value)
          setPage(1)
        }}
        onTagChange={(value) => {
          setTagId(value)
          setPage(1)
        }}
        onFavoriteChange={(value) => {
          setFavorite(value)
          setPage(1)
        }}
        onReset={resetFilters}
        onManageTags={() => {
          setActionError(null)
          setIsTagManagerOpen(true)
        }}
      />

      {actionError && !taggedDocument && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {actionError}
        </p>
      )}

      {isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-20 text-center text-sm text-slate-400 shadow-sm">
          正在加载文档…
        </div>
      ) : loadError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-16 text-center">
          <p className="text-sm text-rose-700">{loadError}</p>
          <button
            type="button"
            onClick={() => void loadDocuments()}
            className="mt-4 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700"
          >
            重新加载
          </button>
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-20 text-center shadow-sm">
          <p className="font-medium text-slate-700">
            {favoritesOnly
              ? '还没有符合条件的收藏文档'
              : isFiltering
                ? '没有符合当前筛选条件的文档'
                : '还没有上传文档'}
          </p>
          <p className="mt-2 text-sm text-slate-400">
            {isFiltering ? '可以清除筛选后重新查看。' : '请先进入知识库上传资料。'}
          </p>
        </div>
      ) : (
        <>
          <DocumentCatalog
            documents={documents}
            knowledgeBases={knowledgeBases}
            updatingFavoriteId={updatingFavoriteId}
            onToggleFavorite={(document) => void handleToggleFavorite(document)}
            onManageTags={(document) => {
              setActionError(null)
              setTaggedDocument(document)
            }}
          />
          <nav className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm">
            <span className="text-slate-500">
              共 {total} 个文档 · 第 {page}/{totalPages} 页
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1 || isOrganizing}
                onClick={() => setPage((current) => current - 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page >= totalPages || isOrganizing}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </nav>
        </>
      )}

      {taggedDocument && (
        <DocumentTagsDialog
          document={taggedDocument}
          tags={tags}
          updatingTagId={updatingTagId}
          error={actionError}
          onAdd={(tag) => void handleAddTag(tag)}
          onRemove={(tag) => void handleRemoveTag(tag)}
          onClose={() => {
            setTaggedDocument(null)
            setActionError(null)
          }}
        />
      )}

      {isTagManagerOpen && (
        <TagManagerDialog
          tags={tags}
          onChange={(updatedTags) => {
            setTags(updatedTags)
            if (tagId !== null && !updatedTags.some((tag) => tag.id === tagId)) {
              setTagId(null)
              setPage(1)
            } else {
              void loadDocuments()
            }
          }}
          onClose={() => setIsTagManagerOpen(false)}
        />
      )}
    </div>
  )
}
