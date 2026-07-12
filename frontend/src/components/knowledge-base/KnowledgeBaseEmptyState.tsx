interface KnowledgeBaseEmptyStateProps {
  onCreate: () => void
}

export function KnowledgeBaseEmptyState({
  onCreate,
}: KnowledgeBaseEmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-semibold text-indigo-600">
        KB
      </div>
      <h2 className="mt-4 text-lg font-semibold text-slate-900">
        还没有知识库
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        创建第一个知识库，用于归类和管理你的个人资料。
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-6 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
      >
        创建知识库
      </button>
    </div>
  )
}
