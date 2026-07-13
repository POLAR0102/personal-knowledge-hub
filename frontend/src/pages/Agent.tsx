import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  createAgentTask,
  getAgentTask,
  listAgentTasks,
  retryAgentTask,
  saveAgentTaskAsNote,
} from '../api/agent'
import { listKnowledgeBases } from '../api/knowledge-bases'
import { AgentTaskForm } from '../components/agent/AgentTaskForm'
import { AgentTaskList } from '../components/agent/AgentTaskList'
import { AgentTaskResult } from '../components/agent/AgentTaskResult'
import { AgentWorkflow } from '../components/agent/AgentWorkflow'
import type { AgentTask, AgentTaskCreate } from '../types/agent'
import type { KnowledgeBase } from '../types/knowledge-base'
import type { Note } from '../types/note'
import { getApiErrorMessage } from '../utils/api-error'

export function Agent() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseError, setKnowledgeBaseError] = useState<string | null>(null)
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [taskTotal, setTaskTotal] = useState(0)
  const [isLoadingTasks, setIsLoadingTasks] = useState(true)
  const [taskListError, setTaskListError] = useState<string | null>(null)
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null)
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null)
  const [isLoadingTask, setIsLoadingTask] = useState(false)
  const [taskLoadError, setTaskLoadError] = useState<string | null>(null)
  const taskRequestId = useRef(0)
  const [isExecuting, setIsExecuting] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [isSavingNote, setIsSavingNote] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [savedNote, setSavedNote] = useState<Note | null>(null)

  const loadTasks = useCallback(async () => {
    setIsLoadingTasks(true)
    setTaskListError(null)
    try {
      const data = await listAgentTasks({ page: 1, page_size: 100 })
      setTasks(data.items)
      setTaskTotal(data.total)
    } catch (error: unknown) {
      setTaskListError(
        getApiErrorMessage(error, 'Agent 历史任务加载失败，请稍后重试'),
      )
    } finally {
      setIsLoadingTasks(false)
    }
  }, [])

  useEffect(() => {
    void loadTasks()
    listKnowledgeBases({ page: 1, page_size: 100 })
      .then((data) => setKnowledgeBases(data.items))
      .catch((error: unknown) => {
        setKnowledgeBaseError(
          getApiErrorMessage(error, '知识库加载失败，请稍后重试'),
        )
      })
  }, [loadTasks])

  useEffect(() => {
    if (isLoadingTasks || taskListError) return
    const requestedId = Number(searchParams.get('task'))
    const requestedTask = tasks.find((task) => task.id === requestedId)
    const nextId = requestedTask?.id ?? tasks[0]?.id ?? null
    setActiveTaskId(nextId)
    if (nextId !== null && requestedId !== nextId) {
      setSearchParams({ task: String(nextId) }, { replace: true })
    } else if (nextId === null && searchParams.has('task')) {
      setSearchParams({}, { replace: true })
    }
  }, [isLoadingTasks, searchParams, setSearchParams, taskListError, tasks])

  const loadTask = useCallback(async (taskId: number) => {
    const requestId = ++taskRequestId.current
    setIsLoadingTask(true)
    setTaskLoadError(null)
    try {
      const data = await getAgentTask(taskId)
      if (requestId !== taskRequestId.current) return
      setActiveTask(data)
    } catch (error: unknown) {
      if (requestId !== taskRequestId.current) return
      setActiveTask(null)
      setTaskLoadError(
        getApiErrorMessage(error, 'Agent 任务详情加载失败，请稍后重试'),
      )
    } finally {
      if (requestId === taskRequestId.current) {
        setIsLoadingTask(false)
      }
    }
  }, [])

  useEffect(() => {
    setSavedNote(null)
    setActionError(null)
    if (activeTaskId === null) {
      taskRequestId.current += 1
      setActiveTask(null)
      setTaskLoadError(null)
      return
    }
    void loadTask(activeTaskId)
  }, [activeTaskId, loadTask])

  function replaceTask(task: AgentTask) {
    setTasks((current) => [
      task,
      ...current.filter((item) => item.id !== task.id),
    ])
    setActiveTask(task)
  }

  async function handleCreate(data: AgentTaskCreate) {
    if (isExecuting) return
    setIsExecuting(true)
    setFormError(null)
    setActionError(null)
    setSavedNote(null)
    try {
      const task = await createAgentTask(data)
      const isNew = !tasks.some((item) => item.id === task.id)
      replaceTask(task)
      if (isNew) setTaskTotal((current) => current + 1)
      setSearchParams({ task: String(task.id) })
    } catch (error: unknown) {
      setFormError(getApiErrorMessage(error, 'Agent 任务创建失败，请稍后重试'))
    } finally {
      setIsExecuting(false)
    }
  }

  async function handleRetry() {
    if (!activeTask || isRetrying) return
    setIsRetrying(true)
    setActionError(null)
    setSavedNote(null)
    try {
      replaceTask(await retryAgentTask(activeTask.id))
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, 'Agent 任务重试失败，请稍后再试'))
      await loadTask(activeTask.id)
    } finally {
      setIsRetrying(false)
    }
  }

  async function handleSaveNote() {
    if (!activeTask || isSavingNote) return
    setIsSavingNote(true)
    setActionError(null)
    try {
      setSavedNote(await saveAgentTaskAsNote(activeTask.id))
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, 'Agent 结果保存为笔记失败'))
    } finally {
      setIsSavingNote(false)
    }
  }

  const isBusy = isExecuting || isRetrying || isSavingNote
  const activeKnowledgeBaseName =
    knowledgeBases.find(
      (knowledgeBase) => knowledgeBase.id === activeTask?.knowledge_base_id,
    )?.name ?? null

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-r from-slate-950 to-violet-950 p-6 text-white shadow-sm sm:p-8">
        <p className="text-sm font-medium text-violet-300">阶段 F · 轻量 Agent</p>
        <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">知识任务助手</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          基于真实知识库执行资料总结、学习计划和主题笔记任务，并保留引用来源。
        </p>
      </section>

      <AgentWorkflow />

      {knowledgeBaseError && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {knowledgeBaseError}
        </p>
      )}

      <AgentTaskForm
        knowledgeBases={knowledgeBases}
        isSubmitting={isExecuting}
        error={formError}
        onSubmit={handleCreate}
      />

      <section className="grid items-start gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <AgentTaskList
          tasks={tasks}
          total={taskTotal}
          activeTaskId={activeTaskId}
          isLoading={isLoadingTasks}
          error={taskListError}
          disabled={isBusy}
          onSelect={(taskId) => {
            if (taskId !== activeTaskId) {
              setSearchParams({ task: String(taskId) })
            }
          }}
          onRetryLoad={() => void loadTasks()}
        />
        <AgentTaskResult
          task={activeTask}
          knowledgeBaseName={activeKnowledgeBaseName}
          isLoading={isLoadingTask || isExecuting}
          loadError={taskLoadError}
          isRetrying={isRetrying}
          isSavingNote={isSavingNote}
          actionError={actionError}
          savedNote={savedNote}
          onRetry={() => void handleRetry()}
          onSaveNote={() => void handleSaveNote()}
          onReload={() => {
            if (activeTaskId !== null) void loadTask(activeTaskId)
          }}
        />
      </section>
    </div>
  )
}
