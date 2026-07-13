import { useEffect, useState, type FormEvent } from 'react'
import type { AgentTaskCreate, AgentTaskType } from '../../types/agent'
import type { KnowledgeBase } from '../../types/knowledge-base'

const taskOptions: Array<{
  value: AgentTaskType
  label: string
  example: string
}> = [
  {
    value: 'summary',
    label: '资料总结',
    example: '请总结知识库中的核心内容，并按主题分点整理。',
  },
  {
    value: 'study_plan',
    label: '学习计划',
    example: '根据知识库内容，制定一份 7 天学习计划。',
  },
  {
    value: 'topic_note',
    label: '主题笔记',
    example: '围绕系统架构生成一份结构清晰的 Markdown 主题笔记。',
  },
]

interface AgentTaskFormProps {
  knowledgeBases: KnowledgeBase[]
  isSubmitting: boolean
  error: string | null
  onSubmit: (data: AgentTaskCreate) => Promise<void>
}

export function AgentTaskForm({
  knowledgeBases,
  isSubmitting,
  error,
  onSubmit,
}: AgentTaskFormProps) {
  const [knowledgeBaseId, setKnowledgeBaseId] = useState(
    knowledgeBases[0]?.id ?? 0,
  )
  const [taskType, setTaskType] = useState<AgentTaskType>('summary')
  const [taskInput, setTaskInput] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    if (!knowledgeBases.some((item) => item.id === knowledgeBaseId)) {
      setKnowledgeBaseId(knowledgeBases[0]?.id ?? 0)
    }
  }, [knowledgeBaseId, knowledgeBases])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const normalizedInput = taskInput.trim()
    if (!knowledgeBaseId) {
      setValidationError('请选择知识库')
      return
    }
    if (!normalizedInput) {
      setValidationError('请输入任务要求')
      return
    }
    if (normalizedInput.length > 1000) {
      setValidationError('任务要求不能超过 1000 个字符')
      return
    }

    setValidationError(null)
    await onSubmit({
      knowledge_base_id: knowledgeBaseId,
      task_type: taskType,
      task_input: normalizedInput,
    })
  }

  const selectedOption = taskOptions.find((option) => option.value === taskType)

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <div>
        <p className="text-sm font-semibold text-slate-900">创建 Agent 任务</p>
        <p className="mt-1 text-xs leading-5 text-slate-400">
          Agent 会检索所选知识库，并按固定工作流生成结果。
        </p>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-700">
          知识库
          <select
            value={knowledgeBaseId}
            onChange={(event) => setKnowledgeBaseId(Number(event.target.value))}
            disabled={isSubmitting || knowledgeBases.length === 0}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          >
            {knowledgeBases.map((knowledgeBase) => (
              <option key={knowledgeBase.id} value={knowledgeBase.id}>
                {knowledgeBase.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm font-medium text-slate-700">
          任务类型
          <select
            value={taskType}
            onChange={(event) => setTaskType(event.target.value as AgentTaskType)}
            disabled={isSubmitting}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
          >
            {taskOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="mt-4 block text-sm font-medium text-slate-700">
        任务要求
        <textarea
          rows={5}
          maxLength={1000}
          value={taskInput}
          onChange={(event) => setTaskInput(event.target.value)}
          disabled={isSubmitting}
          placeholder={selectedOption?.example}
          className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm leading-6 outline-none focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-100"
        />
        <span className="mt-1 flex items-center justify-between gap-3 text-xs text-slate-400">
          <button
            type="button"
            onClick={() => setTaskInput(selectedOption?.example ?? '')}
            disabled={isSubmitting}
            className="font-medium text-indigo-600 hover:text-indigo-500 disabled:opacity-50"
          >
            使用示例
          </button>
          <span>{taskInput.length}/1000</span>
        </span>
      </label>

      {knowledgeBases.length === 0 && (
        <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          请先创建知识库、上传并索引文档，再执行 Agent 任务。
        </p>
      )}
      {(validationError || error) && (
        <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {validationError || error}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting || knowledgeBases.length === 0 || !taskInput.trim()}
        className="mt-5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? 'Agent 正在执行任务…' : '执行 Agent 任务'}
      </button>
    </form>
  )
}
