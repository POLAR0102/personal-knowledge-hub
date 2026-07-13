import type { AgentTaskStatus, AgentTaskType } from '../types/agent'

export const agentTaskTypeLabels: Record<AgentTaskType, string> = {
  summary: '资料总结',
  study_plan: '学习计划',
  topic_note: '主题笔记',
}

export const agentTaskStatusViews: Record<
  AgentTaskStatus,
  { label: string; className: string }
> = {
  pending: { label: '等待执行', className: 'bg-slate-100 text-slate-600' },
  running: { label: '执行中', className: 'bg-amber-50 text-amber-700' },
  completed: { label: '已完成', className: 'bg-emerald-50 text-emerald-700' },
  failed: { label: '失败', className: 'bg-rose-50 text-rose-700' },
}

export function getAgentTaskErrorMessage(message: string | null): string {
  if (!message) return 'Agent 任务执行失败，请稍后重试'
  const messages: Record<string, string> = {
    'Agent service is not configured': 'Agent 服务尚未配置',
    'Unable to load Agent services': 'Agent 服务加载失败，请稍后重试',
    'Knowledge base not found': '知识库不存在或无权访问',
    'Agent task input is invalid': 'Agent 任务要求无效',
    'Unable to retrieve knowledge base content': '无法检索知识库内容，请检查文档索引',
    'Unable to generate Agent result': 'AI 无法生成任务结果，请稍后重试',
  }
  return messages[message] ?? message
}
