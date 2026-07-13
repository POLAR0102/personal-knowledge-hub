import type { KnowledgeBase } from '../../types/knowledge-base'

interface KnowledgeBaseSelectorProps {
  knowledgeBases: KnowledgeBase[]
  knowledgeBaseId: number | null
  disabled: boolean
  onChange: (knowledgeBaseId: number) => void
}

export function KnowledgeBaseSelector({
  knowledgeBases,
  knowledgeBaseId,
  disabled,
  onChange,
}: KnowledgeBaseSelectorProps) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      问答知识库
      <select
        value={knowledgeBaseId ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
      >
        {knowledgeBases.length === 0 && <option value="">暂无知识库</option>}
        {knowledgeBases.map((knowledgeBase) => (
          <option key={knowledgeBase.id} value={knowledgeBase.id}>
            {knowledgeBase.name}
          </option>
        ))}
      </select>
    </label>
  )
}
