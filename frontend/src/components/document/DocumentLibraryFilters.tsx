import type { FormEvent } from 'react'
import type { DocumentStatus } from '../../types/document'
import type { KnowledgeBase } from '../../types/knowledge-base'
import type { Tag } from '../../types/tag'

export type FavoriteFilter = 'all' | 'favorite' | 'not_favorite'

interface DocumentLibraryFiltersProps {
  filenameInput: string
  status: DocumentStatus | null
  knowledgeBaseId: number | null
  tagId: number | null
  favorite: FavoriteFilter
  favoritesOnly: boolean
  knowledgeBases: KnowledgeBase[]
  tags: Tag[]
  disabled: boolean
  onFilenameInputChange: (value: string) => void
  onSearch: () => void
  onStatusChange: (value: DocumentStatus | null) => void
  onKnowledgeBaseChange: (value: number | null) => void
  onTagChange: (value: number | null) => void
  onFavoriteChange: (value: FavoriteFilter) => void
  onReset: () => void
  onManageTags: () => void
}

export function DocumentLibraryFilters({
  filenameInput,
  status,
  knowledgeBaseId,
  tagId,
  favorite,
  favoritesOnly,
  knowledgeBases,
  tags,
  disabled,
  onFilenameInputChange,
  onSearch,
  onStatusChange,
  onKnowledgeBaseChange,
  onTagChange,
  onFavoriteChange,
  onReset,
  onManageTags,
}: DocumentLibraryFiltersProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch()
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <form onSubmit={handleSubmit} className="grid gap-3 lg:grid-cols-[minmax(15rem,1.5fr)_repeat(4,minmax(8rem,1fr))]">
        <div className="flex min-w-0 gap-2">
          <input
            value={filenameInput}
            maxLength={255}
            disabled={disabled}
            onChange={(event) => onFilenameInputChange(event.target.value)}
            placeholder="按文件名搜索"
            className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          />
          <button
            type="submit"
            disabled={disabled}
            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            搜索
          </button>
        </div>

        <select
          aria-label="处理状态"
          value={status ?? ''}
          disabled={disabled}
          onChange={(event) =>
            onStatusChange((event.target.value || null) as DocumentStatus | null)
          }
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 disabled:bg-slate-100"
        >
          <option value="">全部状态</option>
          <option value="pending">等待处理</option>
          <option value="processing">处理中</option>
          <option value="completed">处理完成</option>
          <option value="failed">处理失败</option>
        </select>

        <select
          aria-label="知识库"
          value={knowledgeBaseId ?? ''}
          disabled={disabled}
          onChange={(event) =>
            onKnowledgeBaseChange(event.target.value ? Number(event.target.value) : null)
          }
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 disabled:bg-slate-100"
        >
          <option value="">全部知识库</option>
          {knowledgeBases.map((knowledgeBase) => (
            <option key={knowledgeBase.id} value={knowledgeBase.id}>
              {knowledgeBase.name}
            </option>
          ))}
        </select>

        <select
          aria-label="标签"
          value={tagId ?? ''}
          disabled={disabled}
          onChange={(event) =>
            onTagChange(event.target.value ? Number(event.target.value) : null)
          }
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 disabled:bg-slate-100"
        >
          <option value="">全部标签</option>
          {tags.map((tag) => (
            <option key={tag.id} value={tag.id}>
              {tag.name}
            </option>
          ))}
        </select>

        {!favoritesOnly ? (
          <select
            aria-label="收藏状态"
            value={favorite}
            disabled={disabled}
            onChange={(event) => onFavoriteChange(event.target.value as FavoriteFilter)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 disabled:bg-slate-100"
          >
            <option value="all">全部收藏状态</option>
            <option value="favorite">仅已收藏</option>
            <option value="not_favorite">仅未收藏</option>
          </select>
        ) : (
          <div className="flex items-center rounded-xl bg-amber-50 px-3 py-2.5 text-sm font-medium text-amber-700">
            ★ 仅显示收藏
          </div>
        )}
      </form>

      <div className="mt-4 flex flex-wrap justify-between gap-3 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={onManageTags}
          disabled={disabled}
          className="rounded-lg border border-indigo-200 px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
        >
          管理标签
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={disabled}
          className="text-xs font-medium text-slate-500 hover:text-slate-700 disabled:opacity-50"
        >
          清除全部筛选
        </button>
      </div>
    </section>
  )
}
