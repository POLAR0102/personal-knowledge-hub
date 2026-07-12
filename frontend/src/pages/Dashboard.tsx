import { useEffect, useState } from 'react'
import { getHealth } from '../api/health'
import type { ApiConnectionStatus } from '../types/health'

const summaryCards = [
  { label: '知识库', value: '—', caption: '等待业务模块接入' },
  { label: '文档', value: '—', caption: '等待业务模块接入' },
  { label: '笔记', value: '—', caption: '等待业务模块接入' },
  { label: '问答会话', value: '—', caption: '等待业务模块接入' },
]

export function Dashboard() {
  const [status, setStatus] = useState<ApiConnectionStatus>('checking')

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

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-5 rounded-2xl bg-gradient-to-r from-slate-950 to-slate-800 p-6 text-white shadow-sm sm:p-8 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-indigo-300">欢迎回来</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            你的智能知识工作台
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            在这里管理个人资料、发起知识问答，并让 Agent 帮你整理信息。
          </p>
        </div>
        <span className="w-fit rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          当前阶段：前端初始化
        </span>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <article
            key={card.label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">{card.label}</p>
            <p className="mt-3 text-3xl font-semibold text-slate-900">
              {card.value}
            </p>
            <p className="mt-2 text-xs text-slate-400">{card.caption}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">开始使用</p>
              <p className="mt-1 text-sm text-slate-500">
                后续任务将逐步开放完整知识管理流程
              </p>
            </div>
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
              开发中
            </span>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {['创建知识库', '上传个人文档', '开始 AI 问答'].map(
              (step, index) => (
                <div
                  key={step}
                  className="rounded-xl border border-slate-100 bg-slate-50 p-4"
                >
                  <span className="text-xs font-semibold text-indigo-600">
                    0{index + 1}
                  </span>
                  <p className="mt-2 text-sm font-medium text-slate-700">
                    {step}
                  </p>
                </div>
              ),
            )}
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
