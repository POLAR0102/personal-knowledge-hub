import { Link } from 'react-router-dom'

export function Documents() {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-semibold text-indigo-600">
        文
      </div>
      <h2 className="mt-4 text-xl font-semibold text-slate-900">文档管理</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
        文档归属于具体知识库。请先选择一个知识库，再上传和管理 TXT、Markdown、PDF 或 DOCX 文件。
      </p>
      <Link
        to="/knowledge-bases"
        className="mt-6 inline-flex rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
      >
        选择知识库
      </Link>
    </section>
  )
}
