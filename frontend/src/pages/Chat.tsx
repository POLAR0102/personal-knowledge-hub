import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  sendConversationMessage,
} from '../api/conversations'
import { listKnowledgeBases } from '../api/knowledge-bases'
import { ChatInput } from '../components/chat/ChatInput'
import { ConversationSidebar } from '../components/chat/ConversationSidebar'
import { ConversationThread } from '../components/chat/ConversationThread'
import { DeleteConversationDialog } from '../components/chat/DeleteConversationDialog'
import { NewConversationDialog } from '../components/chat/NewConversationDialog'
import type {
  Conversation,
  ConversationCreate,
  ConversationDetail,
  ConversationMessage,
} from '../types/conversation'
import type { KnowledgeBase } from '../types/knowledge-base'
import { getApiErrorMessage } from '../utils/api-error'

const CONVERSATION_PAGE_SIZE = 100

export function Chat() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationTotal, setConversationTotal] = useState(0)
  const [isLoadingConversations, setIsLoadingConversations] = useState(true)
  const [conversationListError, setConversationListError] = useState<string | null>(null)
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null)
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const detailRequestId = useRef(0)

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseError, setKnowledgeBaseError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [deletingConversation, setDeletingConversation] = useState<Conversation | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(4)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pendingContent, setPendingContent] = useState<string | null>(null)
  const [pendingRequestId, setPendingRequestId] = useState<string | null>(null)
  const [queryError, setQueryError] = useState<string | null>(null)

  const loadConversations = useCallback(async () => {
    setIsLoadingConversations(true)
    setConversationListError(null)
    try {
      const data = await listConversations({
        page: 1,
        page_size: CONVERSATION_PAGE_SIZE,
      })
      setConversations(data.items)
      setConversationTotal(data.total)
    } catch (error: unknown) {
      setConversationListError(
        getApiErrorMessage(error, '会话列表加载失败，请稍后重试'),
      )
    } finally {
      setIsLoadingConversations(false)
    }
  }, [])

  useEffect(() => {
    void loadConversations()
    listKnowledgeBases({ page: 1, page_size: 100 })
      .then((data) => setKnowledgeBases(data.items))
      .catch((error: unknown) => {
        setKnowledgeBaseError(
          getApiErrorMessage(error, '知识库加载失败，请稍后重试'),
        )
      })
  }, [loadConversations])

  useEffect(() => {
    if (isLoadingConversations || conversationListError) return

    const requestedId = Number(searchParams.get('conversation'))
    const requestedConversation = conversations.find(
      (conversation) => conversation.id === requestedId,
    )
    const nextId = requestedConversation?.id ?? conversations[0]?.id ?? null

    setActiveConversationId(nextId)
    if (nextId !== null && requestedId !== nextId) {
      setSearchParams({ conversation: String(nextId) }, { replace: true })
    } else if (nextId === null && searchParams.has('conversation')) {
      setSearchParams({}, { replace: true })
    }
  }, [
    conversations,
    conversationListError,
    isLoadingConversations,
    searchParams,
    setSearchParams,
  ])

  const loadDetail = useCallback(async (conversationId: number) => {
    const requestId = ++detailRequestId.current
    setIsLoadingDetail(true)
    setDetailError(null)
    try {
      const data = await getConversation(conversationId)
      if (requestId !== detailRequestId.current) return null
      setDetail(data)
      return data
    } catch (error: unknown) {
      if (requestId !== detailRequestId.current) return null
      setDetail(null)
      setDetailError(getApiErrorMessage(error, '会话内容加载失败，请稍后重试'))
      return null
    } finally {
      if (requestId === detailRequestId.current) {
        setIsLoadingDetail(false)
      }
    }
  }, [])

  useEffect(() => {
    if (activeConversationId === null) {
      detailRequestId.current += 1
      setDetail(null)
      setDetailError(null)
      return
    }
    void loadDetail(activeConversationId)
  }, [activeConversationId, loadDetail])

  function handleSelectConversation(conversationId: number) {
    if (isSubmitting || conversationId === activeConversationId) return
    setQuestion('')
    setQueryError(null)
    setSearchParams({ conversation: String(conversationId) })
  }

  async function handleCreate(data: ConversationCreate) {
    if (isCreating) return
    setIsCreating(true)
    setActionError(null)
    try {
      const created = await createConversation(data)
      setConversations((current) => [
        created,
        ...current.filter((conversation) => conversation.id !== created.id),
      ])
      setConversationTotal((current) => current + 1)
      setShowCreateDialog(false)
      setSearchParams({ conversation: String(created.id) })
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '会话创建失败，请稍后重试'))
    } finally {
      setIsCreating(false)
    }
  }

  async function handleDelete() {
    if (!deletingConversation || isDeleting) return
    setIsDeleting(true)
    setActionError(null)
    try {
      await deleteConversation(deletingConversation.id)
      const remaining = conversations.filter(
        (conversation) => conversation.id !== deletingConversation.id,
      )
      setConversations(remaining)
      setConversationTotal((current) => Math.max(0, current - 1))
      setDeletingConversation(null)
      if (deletingConversation.id === activeConversationId) {
        const nextId = remaining[0]?.id
        setSearchParams(nextId ? { conversation: String(nextId) } : {})
      }
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '会话删除失败，请稍后重试'))
    } finally {
      setIsDeleting(false)
    }
  }

  async function submitMessage(
    content: string,
    clientRequestId: string,
  ) {
    if (isSubmitting || activeConversationId === null) return
    if (!Number.isInteger(topK) || topK < 1 || topK > 10) {
      setQueryError('检索片段数必须在 1 到 10 之间')
      return
    }

    setIsSubmitting(true)
    setQueryError(null)
    setPendingContent(content)
    setPendingRequestId(clientRequestId)
    try {
      await sendConversationMessage(activeConversationId, {
        content,
        top_k: topK,
        client_request_id: clientRequestId,
      })
      setQuestion('')
      await loadDetail(activeConversationId)
      await loadConversations()
    } catch (error: unknown) {
      setQueryError(getApiErrorMessage(error, '回答生成失败，可以稍后重试这条问题'))
      await loadDetail(activeConversationId)
    } finally {
      setPendingContent(null)
      setPendingRequestId(null)
      setIsSubmitting(false)
    }
  }

  function handleSend() {
    const normalizedQuestion = question.trim()
    if (!normalizedQuestion) return
    void submitMessage(normalizedQuestion, crypto.randomUUID())
  }

  function handleRetry(message: ConversationMessage) {
    if (!message.client_request_id) return
    void submitMessage(message.content, message.client_request_id)
  }

  const selectedKnowledgeBase = useMemo(
    () => knowledgeBases.find(
      (knowledgeBase) => knowledgeBase.id === detail?.knowledge_base_id,
    ),
    [detail?.knowledge_base_id, knowledgeBases],
  )
  const lastMessage = detail?.messages.at(-1)
  const hasUnresolvedMessage =
    lastMessage?.role === 'user' &&
    (lastMessage.request_status === 'processing' ||
      lastMessage.request_status === 'failed')

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-r from-slate-950 to-indigo-950 p-6 text-white shadow-sm sm:p-8">
        <p className="text-sm font-medium text-indigo-300">阶段 E · 会话与历史记录</p>
        <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">知识库问答</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          问题、AI 回答和当时的真实引用会保存到会话中，刷新页面后仍可继续查看。
        </p>
        <p className="mt-2 text-xs text-slate-400">
          当前每条问题都会独立执行 RAG 检索，历史消息暂不参与下一轮回答的 Prompt。
        </p>
      </section>

      {knowledgeBaseError && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {knowledgeBaseError}
        </p>
      )}

      <section className="grid items-start gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <ConversationSidebar
          conversations={conversations}
          total={conversationTotal}
          activeConversationId={activeConversationId}
          disabled={isSubmitting}
          isLoading={isLoadingConversations}
          error={conversationListError}
          onCreate={() => {
            setActionError(null)
            setShowCreateDialog(true)
          }}
          onSelect={handleSelectConversation}
          onDelete={(conversation) => {
            setActionError(null)
            setDeletingConversation(conversation)
          }}
          onRetry={() => void loadConversations()}
        />

        <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          {activeConversationId === null ? (
            <div className="flex min-h-96 items-center justify-center text-center">
              <div>
                <p className="font-semibold text-slate-800">选择或新建一个问答会话</p>
                <p className="mt-2 text-sm text-slate-400">新建会话时需要选择本次问答使用的知识库。</p>
              </div>
            </div>
          ) : isLoadingDetail ? (
            <p className="py-24 text-center text-sm text-slate-400">正在加载会话消息…</p>
          ) : detailError || !detail ? (
            <div className="py-20 text-center">
              <p className="text-sm text-rose-700">{detailError || '会话不存在'}</p>
              <button
                type="button"
                onClick={() => void loadDetail(activeConversationId)}
                className="mt-4 rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50"
              >
                重新加载
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <header className="border-b border-slate-100 pb-4">
                <h3 className="break-words text-lg font-semibold text-slate-900">{detail.title}</h3>
                <p className="mt-1 text-xs text-slate-400">
                  知识库：{selectedKnowledgeBase?.name ?? `#${detail.knowledge_base_id}`}
                </p>
              </header>

              <ConversationThread
                messages={detail.messages}
                isSubmitting={isSubmitting}
                pendingContent={pendingContent}
                pendingRequestId={pendingRequestId}
                onRetry={handleRetry}
              />

              {queryError && (
                <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{queryError}</p>
              )}
              {hasUnresolvedMessage && lastMessage?.request_status === 'failed' && (
                <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  上一条问题生成失败，请先点击消息下方的“重新尝试”。
                </p>
              )}

              <div className="border-t border-slate-100 pt-5">
                <ChatInput
                  question={question}
                  topK={topK}
                  isSubmitting={isSubmitting}
                  disabled={hasUnresolvedMessage}
                  onQuestionChange={setQuestion}
                  onTopKChange={setTopK}
                  onSubmit={handleSend}
                />
              </div>
            </div>
          )}
        </div>
      </section>

      {showCreateDialog && (
        <NewConversationDialog
          knowledgeBases={knowledgeBases}
          isSubmitting={isCreating}
          error={actionError}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreateDialog(false)
            setActionError(null)
          }}
        />
      )}

      {deletingConversation && (
        <DeleteConversationDialog
          conversation={deletingConversation}
          isDeleting={isDeleting}
          error={actionError}
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            setDeletingConversation(null)
            setActionError(null)
          }}
        />
      )}
    </div>
  )
}
