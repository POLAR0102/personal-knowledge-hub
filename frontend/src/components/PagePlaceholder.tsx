interface PagePlaceholderProps {
  eyebrow: string
  title: string
  description: string
}

export function PagePlaceholder({
  eyebrow,
  title,
  description,
}: PagePlaceholderProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-sm font-bold text-indigo-600">
        {eyebrow}
      </div>
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
        {title}
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
        {description}
      </p>
      <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 py-10 text-center text-sm text-slate-400">
        该模块将在后续开发任务中开放
      </div>
    </section>
  )
}
