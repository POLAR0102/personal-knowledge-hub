import { useEffect, useState } from 'react'
import { listKnowledgeBases } from '../api/knowledge-bases'
import { semanticSearch } from '../api/rag'
import { SemanticSearchForm } from '../components/semantic-search/SemanticSearchForm'
import { SemanticSearchResults } from '../components/semantic-search/SemanticSearchResults'
import type { KnowledgeBase } from '../types/knowledge-base'
import type { SemanticSearchResult } from '../types/semantic-search'
import { getApiErrorMessage } from '../utils/api-error'

export function SemanticSearch() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(4)
  const [results, setResults] = useState<SemanticSearchResult[] | null>(null)
  const [isLoadingKnowledgeBases, setIsLoadingKnowledgeBases] = useState(true)
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listKnowledgeBases({ page: 1, page_size: 100 })
      .then((data) => {
        if (cancelled) return
        setKnowledgeBases(data.items)
        setKnowledgeBaseId((current) => current ?? data.items[0]?.id ?? null)
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(getApiErrorMessage(requestError, '知识库加载失败，请稍后重试'))
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingKnowledgeBases(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSearch() {
    const normalizedQuery = query.trim()
    if (knowledgeBaseId === null) {
      setError('请先选择知识库')
      return
    }
    if (!normalizedQuery) {
      setError('请输入检索问题')
      return
    }
    if (!Number.isInteger(topK) || topK < 1 || topK > 20) {
      setError('返回片段数必须是 1 到 20 的整数')
      return
    }

    setIsSearching(true)
    setError(null)
    setResults(null)
    try {
      const response = await semanticSearch({
        knowledge_base_id: knowledgeBaseId,
        query: normalizedQuery,
        top_k: topK,
      })
      setResults(response.results)
    } catch (requestError: unknown) {
      setError(getApiErrorMessage(requestError, '语义检索失败，请稍后重试'))
    } finally {
      setIsSearching(false)
    }
  }

  const disabled = isLoadingKnowledgeBases || knowledgeBases.length === 0

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-r from-slate-950 to-indigo-950 p-6 text-white shadow-sm sm:p-8">
        <p className="text-sm font-medium text-indigo-300">知识库检索工具</p>
        <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">语义检索</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          直接查看向量检索返回的真实文档片段和距离。本页面不调用 Chat Model，也不会生成 AI 回答。
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        {error && (
          <p className="mb-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}
        <SemanticSearchForm
          knowledgeBases={knowledgeBases}
          knowledgeBaseId={knowledgeBaseId}
          query={query}
          topK={topK}
          isSearching={isSearching}
          disabled={disabled}
          onKnowledgeBaseChange={(id) => {
            setKnowledgeBaseId(id)
            setResults(null)
            setError(null)
          }}
          onQueryChange={(value) => {
            setQuery(value)
            setResults(null)
            setError(null)
          }}
          onTopKChange={setTopK}
          onSubmit={() => void handleSearch()}
        />
        {!isLoadingKnowledgeBases && knowledgeBases.length === 0 && (
          <p className="mt-5 text-sm text-slate-500">
            尚未创建知识库，请先创建知识库并完成文档索引。
          </p>
        )}
      </section>

      {results !== null && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="mb-5">
            <h3 className="font-semibold text-slate-900">检索结果</h3>
            <p className="mt-1 text-xs text-slate-400">
              共返回 {results.length} 个已索引片段，按相关性排列
            </p>
          </div>
          <SemanticSearchResults results={results} />
        </section>
      )}
    </div>
  )
}
