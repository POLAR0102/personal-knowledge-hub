import type { RagCitation } from './rag'

export type AgentTaskType = 'summary' | 'study_plan' | 'topic_note'
export type AgentTaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AgentTask {
  id: number
  user_id: number
  knowledge_base_id: number
  task_type: AgentTaskType
  task_input: string
  status: AgentTaskStatus
  result_content: string | null
  citations: RagCitation[]
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AgentTaskCreate {
  knowledge_base_id: number
  task_type: AgentTaskType
  task_input: string
}

export interface AgentTaskListResponse {
  items: AgentTask[]
  total: number
  page: number
  page_size: number
}
