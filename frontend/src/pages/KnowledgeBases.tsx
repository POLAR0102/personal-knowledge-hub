import { useCallback, useEffect, useState } from 'react'
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
} from '../api/knowledge-bases'
import { DeleteKnowledgeBaseDialog } from '../components/knowledge-base/DeleteKnowledgeBaseDialog'
import { KnowledgeBaseCard } from '../components/knowledge-base/KnowledgeBaseCard'
import { KnowledgeBaseEmptyState } from '../components/knowledge-base/KnowledgeBaseEmptyState'
import { KnowledgeBaseForm } from '../components/knowledge-base/KnowledgeBaseForm'
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
} from '../types/knowledge-base'
import { getApiErrorMessage } from '../utils/api-error'

const PAGE_SIZE = 6

export function KnowledgeBases() {
  const [items, setItems] = useState<KnowledgeBase[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null)
  const [editingItem, setEditingItem] = useState<KnowledgeBase | null>(null)
  const [deletingItem, setDeletingItem] = useState<KnowledgeBase | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadItems = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await listKnowledgeBases({ page, page_size: PAGE_SIZE })
      setItems(data.items)
      setTotal(data.total)
    } catch (error: unknown) {
      setLoadError(getApiErrorMessage(error, '知识库列表加载失败，请稍后重试'))
    } finally {
      setIsLoading(false)
    }
  }, [page])

  useEffect(() => {
    void loadItems()
  }, [loadItems])

  function openCreateForm() {
    setActionError(null)
    setEditingItem(null)
    setFormMode('create')
  }

  function openEditForm(item: KnowledgeBase) {
    setActionError(null)
    setEditingItem(item)
    setFormMode('edit')
  }

  function openDeleteDialog(item: KnowledgeBase) {
    setActionError(null)
    setDeletingItem(item)
  }

  async function handleFormSubmit(data: KnowledgeBaseCreate) {
    if (isSubmitting) return
    setIsSubmitting(true)
    setActionError(null)
    try {
      if (formMode === 'edit' && editingItem) {
        const updated = await updateKnowledgeBase(editingItem.id, data)
        setItems((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        )
      } else {
        await createKnowledgeBase(data)
        if (page !== 1) {
          setPage(1)
        } else {
          await loadItems()
        }
      }
      setFormMode(null)
      setEditingItem(null)
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '知识库保存失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!deletingItem || isDeleting) return
    setIsDeleting(true)
    setActionError(null)
    try {
      await deleteKnowledgeBase(deletingItem.id)
      setDeletingItem(null)
      if (items.length === 1 && page > 1) {
        setPage((current) => current - 1)
      } else {
        await loadItems()
      }
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '知识库删除失败，请稍后重试'))
    } finally {
      setIsDeleting(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-indigo-600">个人资料空间</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-900">知识库</h2>
          <p className="mt-2 text-sm text-slate-500">
            创建和管理知识库。当前共 {total} 个知识库。
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateForm}
          className="w-fit rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
        >
          + 创建知识库
        </button>
      </section>

      {isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-sm text-slate-500 shadow-sm">
          正在加载知识库…
        </div>
      ) : loadError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-12 text-center">
          <p className="text-sm text-rose-700">{loadError}</p>
          <button
            type="button"
            onClick={() => void loadItems()}
            className="mt-4 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100"
          >
            重新加载
          </button>
        </div>
      ) : items.length === 0 ? (
        <KnowledgeBaseEmptyState onCreate={openCreateForm} />
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((item) => (
              <KnowledgeBaseCard
                key={item.id}
                knowledgeBase={item}
                onEdit={openEditForm}
                onDelete={openDeleteDialog}
              />
            ))}
          </section>

          <nav
            aria-label="知识库分页"
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm"
          >
            <span className="text-slate-500">
              第 {page} / {totalPages} 页
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </nav>
        </>
      )}

      {formMode && (
        <KnowledgeBaseForm
          key={editingItem?.id ?? 'create'}
          mode={formMode}
          initialValue={editingItem ?? undefined}
          isSubmitting={isSubmitting}
          error={actionError}
          onSubmit={handleFormSubmit}
          onCancel={() => {
            setFormMode(null)
            setEditingItem(null)
            setActionError(null)
          }}
        />
      )}

      {deletingItem && (
        <DeleteKnowledgeBaseDialog
          knowledgeBase={deletingItem}
          isDeleting={isDeleting}
          error={actionError}
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            setDeletingItem(null)
            setActionError(null)
          }}
        />
      )}
    </div>
  )
}
