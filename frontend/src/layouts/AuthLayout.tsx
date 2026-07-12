import { Link, Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="grid min-h-screen bg-slate-50 lg:grid-cols-2">
      <section className="hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500 font-bold">
            K
          </span>
          <span className="font-semibold">智能个人知识库</span>
        </Link>
        <div className="max-w-lg">
          <p className="text-sm font-medium text-indigo-300">RAG + Agent</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight">
            让个人资料真正成为可以对话的知识
          </h1>
          <p className="mt-5 text-sm leading-7 text-slate-400">
            统一管理文档，通过检索增强生成获得带引用的答案，并使用 Agent
            完成知识整理任务。
          </p>
        </div>
        <p className="text-xs text-slate-600">本科毕业设计 · 演示版本</p>
      </section>
      <main className="flex items-center justify-center p-6 sm:p-10">
        <Outlet />
      </main>
    </div>
  )
}
