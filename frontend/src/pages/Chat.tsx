import { useEffect, useState } from 'react'
import { listKnowledgeBases } from '../api/knowledge-bases'
import { queryKnowledgeBase } from '../api/rag'
import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessage } from '../components/chat/ChatMessage'
import { CitationList } from '../components/chat/CitationList'
import { KnowledgeBaseSelector } from '../components/chat/KnowledgeBaseSelector'
import type { KnowledgeBase } from '../types/knowledge-base'
import type { RagQueryResponse } from '../types/rag'
import { getApiErrorMessage } from '../utils/api-error'

export function Chat() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<number | null>(null)
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(4)
  const [isLoadingKnowledgeBases, setIsLoadingKnowledgeBases] = useState(true)
  const [knowledgeBaseError, setKnowledgeBaseError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [queryError, setQueryError] = useState<string | null>(null)
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null)
  const [response, setResponse] = useState<RagQueryResponse | null>(null)

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

  function handleKnowledgeBaseChange(id: number) {
    setKnowledgeBaseId(id)
    setSubmittedQuestion(null)
    setResponse(null)
    setQueryError(null)
  }

  async function handleQuery() {
    const normalizedQuestion = question.trim()
    if (isSubmitting || knowledgeBaseId === null || !normalizedQuestion) return
    if (!Number.isInteger(topK) || topK < 1 || topK > 10) {
      setQueryError('检索片段数必须在 1 到 10 之间')
      return
    }

    setIsSubmitting(true)
    setQueryError(null)
    setSubmittedQuestion(normalizedQuestion)
    setResponse(null)
    try {
      setResponse(
        await queryKnowledgeBase({
          knowledge_base_id: knowledgeBaseId,
          question: normalizedQuestion,
          top_k: topK,
        }),
      )
      setQuestion('')
    } catch (error: unknown) {
      setQueryError(getApiErrorMessage(error, '知识库问答失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const isFormDisabled = isLoadingKnowledgeBases || knowledgeBases.length === 0

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-r from-slate-950 to-indigo-950 p-6 text-white shadow-sm sm:p-8">
        <p className="text-sm font-medium text-indigo-300">阶段 D · RAG 问答</p>
        <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">知识库问答</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          从已索引文档中检索相关内容并生成回答，引用信息来自真实文档片段。
        </p>
        <p className="mt-2 text-xs text-slate-400">
          当前仅支持单轮问答，不保存聊天历史；历史会话将在后续阶段接入。
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
            请先创建知识库、上传并索引文档，再进行知识库问答。
          </p>
        ) : null}

        {!knowledgeBaseError && (
          <div className="space-y-5">
            <KnowledgeBaseSelector
              knowledgeBases={knowledgeBases}
              knowledgeBaseId={knowledgeBaseId}
              disabled={isFormDisabled || isSubmitting}
              onChange={handleKnowledgeBaseChange}
            />
            <ChatInput
              question={question}
              topK={topK}
              isSubmitting={isSubmitting}
              disabled={isFormDisabled}
              onQuestionChange={setQuestion}
              onTopKChange={setTopK}
              onSubmit={() => void handleQuery()}
            />
          </div>
        )}

        {queryError && (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {queryError}
          </p>
        )}
      </section>

      {submittedQuestion && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="space-y-5">
            <ChatMessage role="user" content={submittedQuestion} />
            {isSubmitting ? (
              <ChatMessage role="assistant" isLoading />
            ) : response ? (
              <>
                <ChatMessage role="assistant" content={response.answer} />
                <div className="ml-0 space-y-3 sm:ml-12">
                  <CitationList citations={response.citations} />
                  <p className="text-xs text-slate-400">
                    检索到 {response.retrieval_count} 个相关片段 · 模型：{response.model}
                  </p>
                </div>
              </>
            ) : null}
          </div>
        </section>
      )}
    </div>
  )
}
