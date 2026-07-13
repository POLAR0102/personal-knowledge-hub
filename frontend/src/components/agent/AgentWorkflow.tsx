const steps = [
  '校验任务与知识库权限',
  '从已索引文档检索真实片段',
  '按任务类型组织上下文并调用模型',
  '保存结果、状态和引用快照',
]

export function AgentWorkflow() {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <p className="text-sm font-semibold text-slate-900">固定工作流</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {steps.map((step, index) => (
          <div key={step} className="rounded-xl bg-slate-50 p-4">
            <span className="text-xs font-bold text-indigo-600">0{index + 1}</span>
            <p className="mt-2 text-sm leading-6 text-slate-700">{step}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs leading-5 text-slate-400">
        此处仅展示可验证的系统步骤，不展示或伪造模型的私有思考过程。
      </p>
    </section>
  )
}
