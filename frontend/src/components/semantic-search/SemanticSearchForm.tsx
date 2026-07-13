import type { FormEvent } from 'react'
import type { KnowledgeBase } from '../../types/knowledge-base'

interface SemanticSearchFormProps {
  knowledgeBases: KnowledgeBase[]
  knowledgeBaseId: number | null
  query: string
  topK: number
  isSearching: boolean
  disabled: boolean
  onKnowledgeBaseChange: (id: number) => void
  onQueryChange: (query: string) => void
  onTopKChange: (topK: number) => void
  onSubmit: () => void
}

export function SemanticSearchForm({
  knowledgeBases,
  knowledgeBaseId,
  query,
  topK,
  isSearching,
  disabled,
  onKnowledgeBaseChange,
  onQueryChange,
  onTopKChange,
  onSubmit,
}: SemanticSearchFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid gap-5 md:grid-cols-[1fr_10rem]">
        <label className="block text-sm font-medium text-slate-700">
          检索知识库
          <select
            value={knowledgeBaseId ?? ''}
            disabled={disabled || isSearching}
            onChange={(event) => onKnowledgeBaseChange(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          >
            {knowledgeBases.length === 0 && <option value="">暂无知识库</option>}
            {knowledgeBases.map((knowledgeBase) => (
              <option key={knowledgeBase.id} value={knowledgeBase.id}>
                {knowledgeBase.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-slate-700">
          返回片段数
          <input
            type="number"
            min={1}
            max={20}
            value={topK}
            disabled={disabled || isSearching}
            onChange={(event) => onTopKChange(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          />
        </label>
      </div>

      <label className="block text-sm font-medium text-slate-700">
        检索问题
        <textarea
          rows={4}
          maxLength={1000}
          value={query}
          disabled={disabled || isSearching}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="例如：核心版本需要多久完成？"
          className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm leading-6 outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
        />
        <span className="mt-1 block text-right text-xs text-slate-400">
          {query.length} / 1000
        </span>
      </label>

      <button
        type="submit"
        disabled={disabled || isSearching || !query.trim()}
        className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSearching ? '正在生成查询向量并检索…' : '开始语义检索'}
      </button>
    </form>
  )
}
