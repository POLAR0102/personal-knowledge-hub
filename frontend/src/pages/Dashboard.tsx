import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getDocumentStats } from '../api/documents'
import { getHealth } from '../api/health'
import { listKnowledgeBases } from '../api/knowledge-bases'
import type { ApiConnectionStatus } from '../types/health'

interface SummaryCardProps {
  label: string
  value: string | number
  caption: string
  to?: string
}

function SummaryCard({ label, value, caption, to }: SummaryCardProps) {
  const content = (
    <article
      className={`h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${
        to
          ? 'transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md'
          : ''
      }`}
    >
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
      <p className="mt-2 text-xs text-slate-400">{caption}</p>
    </article>
  )

  return to ? (
    <Link to={to} className="block rounded-2xl focus:outline-none focus:ring-3 focus:ring-indigo-100">
      {content}
    </Link>
  ) : (
    content
  )
}

interface QuickStepProps {
  index: number
  title: string
  status: string
  to?: string
}

function QuickStep({ index, title, status, to }: QuickStepProps) {
  const content: ReactNode = (
    <div
      className={`h-full rounded-xl border border-slate-100 bg-slate-50 p-4 ${
        to ? 'transition hover:border-indigo-200 hover:bg-indigo-50' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-indigo-600">0{index}</span>
        <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-400">
          {status}
        </span>
      </div>
      <p className="mt-3 text-sm font-medium text-slate-700">{title}</p>
    </div>
  )

  return to ? <Link to={to}>{content}</Link> : content
}

export function Dashboard() {
  const [status, setStatus] = useState<ApiConnectionStatus>('checking')
  const [knowledgeBaseTotal, setKnowledgeBaseTotal] = useState<number | null>(
    null,
  )
  const [knowledgeBaseError, setKnowledgeBaseError] = useState(false)
  const [documentTotal, setDocumentTotal] = useState<number | null>(null)
  const [documentError, setDocumentError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    getHealth({ signal: controller.signal })
      .then((data) => {
        setStatus(data.status === 'ok' ? 'online' : 'offline')
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error('Health check failed', error)
          setStatus('offline')
        }
      })

    return () => controller.abort()
  }, [])

  useEffect(() => {
    listKnowledgeBases({ page: 1, page_size: 1 })
      .then((data) => setKnowledgeBaseTotal(data.total))
      .catch(() => setKnowledgeBaseError(true))
  }, [])

  useEffect(() => {
    getDocumentStats()
      .then((data) => setDocumentTotal(data.total))
      .catch(() => setDocumentError(true))
  }, [])

  const statusView = {
    checking: {
      label: '正在检查 API',
      detail: '正在连接后端服务…',
      dot: 'bg-amber-400',
      panel: 'border-amber-200 bg-amber-50 text-amber-800',
    },
    online: {
      label: 'API 正常',
      detail: '后端服务连接成功',
      dot: 'bg-emerald-500',
      panel: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    },
    offline: {
      label: 'API 连接失败',
      detail: '请确认 FastAPI 已在 8000 端口启动',
      dot: 'bg-rose-500',
      panel: 'border-rose-200 bg-rose-50 text-rose-800',
    },
  }[status]

  const knowledgeBaseCaption = knowledgeBaseError
    ? '暂时无法获取数量'
    : knowledgeBaseTotal === null
      ? '正在获取真实数据…'
      : knowledgeBaseTotal === 0
        ? '尚未创建知识库'
        : '查看和管理知识库'

  const documentCaption = documentError
    ? '暂时无法获取数量'
    : documentTotal === null
      ? '正在获取真实数据…'
      : documentTotal === 0
        ? '尚未上传文档'
        : '选择知识库管理文档'

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-5 rounded-2xl bg-gradient-to-r from-slate-950 to-slate-800 p-6 text-white shadow-sm sm:p-8 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-indigo-300">欢迎回来</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            你的智能知识工作台
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            在这里管理个人资料、建立向量索引，并检索真实文档片段。
          </p>
        </div>
        <span className="w-fit rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          当前阶段：向量索引与语义检索
        </span>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="知识库"
          value={knowledgeBaseTotal ?? '—'}
          caption={knowledgeBaseCaption}
          to="/knowledge-bases"
        />
        <SummaryCard
          label="文档"
          value={documentTotal ?? '—'}
          caption={documentCaption}
          to="/knowledge-bases"
        />
        <SummaryCard label="笔记" value="—" caption="笔记模块尚未接入" />
        <SummaryCard label="问答会话" value="—" caption="问答模块尚未接入" />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">开始使用</p>
              <p className="mt-1 text-sm text-slate-500">
                文档处理、向量索引和语义检索已开放，AI 回答尚未接入
              </p>
            </div>
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
              持续开发
            </span>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <QuickStep
              index={1}
              title="创建知识库"
              status="已开放"
              to="/knowledge-bases"
            />
            <QuickStep
              index={2}
              title="上传个人文档"
              status="已开放"
              to="/knowledge-bases"
            />
            <QuickStep
              index={3}
              title="语义检索"
              status="已开放"
              to="/chat"
            />
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">系统状态</p>
          <div className={`mt-5 rounded-xl border p-4 ${statusView.panel}`}>
            <div className="flex items-center gap-3">
              <span
                className={`h-2.5 w-2.5 rounded-full ${statusView.dot}`}
              />
              <span className="text-sm font-semibold">{statusView.label}</span>
            </div>
            <p className="mt-2 pl-5 text-xs opacity-75">{statusView.detail}</p>
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-400">
            检查地址由 VITE_API_BASE_URL 配置，当前请求 /health。
          </p>
        </article>
      </section>
    </div>
  )
}
