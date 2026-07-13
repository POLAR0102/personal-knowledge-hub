import { useEffect, useState } from 'react'
import { listKnowledgeBases } from '../api/knowledge-bases'
import { semanticSearch } from '../api/rag'
import { SemanticSearchForm } from '../components/semantic-search/SemanticSearchForm'
import { SemanticSearchResults } from '../components/semantic-search/SemanticSearchResults'
import type { KnowledgeBase } from '../types/knowledge-base'
import type { SemanticSearchResponse } from '../types/semantic-search'
import { getApiErrorMessage } from '../utils/api-error'

export function Chat() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(4)
  const [isLoadingKnowledgeBases, setIsLoadingKnowledgeBases] = useState(true)
  const [knowledgeBaseError, setKnowledgeBaseError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [response, setResponse] = useState<SemanticSearchResponse | null>(null)

  useEffect(() => {
    setIsLoadingKnowledgeBases(true)
    listKnowledgeBases({ page: 1, page_size: 100 })
      .then((data) => {
        setKnowledgeBases(data.items)
        setKnowledgeBaseId(data.items[0]?.id ?? null)
      })
      .catch((error: unknown) => {
        setKnowledgeBaseError(getApiErrorMessage(error, '知识库加载失败，请稍后重试'))
      })
      .finally(() => setIsLoadingKnowledgeBases(false))
  }, [])

  async function handleSearch() {
    if (isSearching || knowledgeBaseId === null || !query.trim()) return
    if (!Number.isInteger(topK) || topK < 1 || topK > 20) {
      setSearchError('返回片段数必须在 1 到 20 之间')
      return
    }

    setIsSearching(true)
    setSearchError(null)
    setResponse(null)
    try {
      setResponse(
        await semanticSearch({
          knowledge_base_id: knowledgeBaseId,
          query: query.trim(),
          top_k: topK,
        }),
      )
    } catch (error: unknown) {
      setSearchError(getApiErrorMessage(error, '语义检索失败，请稍后重试'))
    } finally {
      setIsSearching(false)
    }
  }

  const isFormDisabled = isLoadingKnowledgeBases || knowledgeBases.length === 0

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-r from-slate-950 to-indigo-950 p-6 text-white shadow-sm sm:p-8">
        <p className="text-sm font-medium text-indigo-300">阶段 C · 检索调试</p>
        <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">语义检索</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          当前仅展示向量检索得到的真实文档片段，尚未调用大语言模型，也不会生成 AI 回答。
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        {knowledgeBaseError ? (
          <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {knowledgeBaseError}
          </p>
        ) : isLoadingKnowledgeBases ? (
          <p className="py-8 text-center text-sm text-slate-500">正在加载知识库…</p>
        ) : knowledgeBases.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
            请先创建知识库、上传并索引文档，再进行语义检索。
          </p>
        ) : null}

        {!knowledgeBaseError && (
          <SemanticSearchForm
            knowledgeBases={knowledgeBases}
            knowledgeBaseId={knowledgeBaseId}
            query={query}
            topK={topK}
            isSearching={isSearching}
            disabled={isFormDisabled}
            onKnowledgeBaseChange={setKnowledgeBaseId}
            onQueryChange={setQuery}
            onTopKChange={setTopK}
            onSubmit={() => void handleSearch()}
          />
        )}

        {searchError && (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {searchError}
          </p>
        )}
      </section>

      {response && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="mb-5">
            <p className="text-sm font-semibold text-slate-900">语义检索结果</p>
            <p className="mt-1 text-xs text-slate-400">
              返回 {response.results.length} 个已索引片段；结果不是 AI 生成的答案
            </p>
          </div>
          <SemanticSearchResults results={response.results} />
        </section>
      )}
    </div>
  )
}
