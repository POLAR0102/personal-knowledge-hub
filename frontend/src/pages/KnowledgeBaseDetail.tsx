import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  deleteKnowledgeBase,
  getKnowledgeBase,
  updateKnowledgeBase,
} from '../api/knowledge-bases'
import { DeleteKnowledgeBaseDialog } from '../components/knowledge-base/DeleteKnowledgeBaseDialog'
import { KnowledgeBaseForm } from '../components/knowledge-base/KnowledgeBaseForm'
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
} from '../types/knowledge-base'
import { getApiErrorMessage } from '../utils/api-error'
import { formatDateTime } from '../utils/date'

export function KnowledgeBaseDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const knowledgeBaseId = Number(id)
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    if (!Number.isInteger(knowledgeBaseId) || knowledgeBaseId <= 0) {
      setLoadError('知识库地址无效')
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setLoadError(null)
    getKnowledgeBase(knowledgeBaseId)
      .then(setKnowledgeBase)
      .catch((error: unknown) => {
        setLoadError(getApiErrorMessage(error, '知识库加载失败，请稍后重试'))
      })
      .finally(() => setIsLoading(false))
  }, [knowledgeBaseId])

  async function handleUpdate(data: KnowledgeBaseCreate) {
    if (!knowledgeBase || isSubmitting) return
    setIsSubmitting(true)
    setActionError(null)
    try {
      const updated = await updateKnowledgeBase(knowledgeBase.id, data)
      setKnowledgeBase(updated)
      setIsEditing(false)
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '知识库保存失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!knowledgeBase || isDeleting) return
    setIsDeleting(true)
    setActionError(null)
    try {
      await deleteKnowledgeBase(knowledgeBase.id)
      navigate('/knowledge-bases', { replace: true })
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '知识库删除失败，请稍后重试'))
      setIsDeleting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-sm text-slate-500 shadow-sm">
        正在加载知识库详情…
      </div>
    )
  }

  if (loadError || !knowledgeBase) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-12 text-center">
        <p className="text-sm text-rose-700">{loadError || '知识库不存在'}</p>
        <Link
          to="/knowledge-bases"
          className="mt-4 inline-flex rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100"
        >
          返回知识库列表
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        to="/knowledge-bases"
        className="inline-flex text-sm font-medium text-slate-500 hover:text-indigo-600"
      >
        ← 返回知识库列表
      </Link>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div className="min-w-0">
            <p className="text-sm font-medium text-indigo-600">知识库详情</p>
            <h2 className="mt-2 break-words text-2xl font-semibold text-slate-900 sm:text-3xl">
              {knowledgeBase.name}
            </h2>
            <p className="mt-4 max-w-3xl whitespace-pre-wrap text-sm leading-7 text-slate-500">
              {knowledgeBase.description || '暂无描述'}
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => {
                setActionError(null)
                setIsEditing(true)
              }}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
            >
              编辑
            </button>
            <button
              type="button"
              onClick={() => {
                setActionError(null)
                setIsConfirmingDelete(true)
              }}
              className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50"
            >
              删除
            </button>
          </div>
        </div>

        <dl className="mt-8 grid gap-4 border-t border-slate-100 pt-6 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-400">创建时间</dt>
            <dd className="mt-1 font-medium text-slate-700">
              {formatDateTime(knowledgeBase.created_at)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">更新时间</dt>
            <dd className="mt-1 font-medium text-slate-700">
              {formatDateTime(knowledgeBase.updated_at)}
            </dd>
          </div>
        </dl>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div>
          <p className="text-sm font-semibold text-slate-900">知识库文档</p>
          <p className="mt-1 text-sm text-slate-500">管理该知识库中的资料</p>
        </div>
        <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
          <p className="text-sm font-medium text-slate-700">文档模块尚未接入</p>
          <p className="mt-2 text-xs text-slate-400">
            后续将支持文档上传、解析与向量化处理。
          </p>
        </div>
      </section>

      {isEditing && (
        <KnowledgeBaseForm
          key={knowledgeBase.id}
          mode="edit"
          initialValue={knowledgeBase}
          isSubmitting={isSubmitting}
          error={actionError}
          onSubmit={handleUpdate}
          onCancel={() => {
            setIsEditing(false)
            setActionError(null)
          }}
        />
      )}

      {isConfirmingDelete && (
        <DeleteKnowledgeBaseDialog
          knowledgeBase={knowledgeBase}
          isDeleting={isDeleting}
          error={actionError}
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            setIsConfirmingDelete(false)
            setActionError(null)
          }}
        />
      )}
    </div>
  )
}
