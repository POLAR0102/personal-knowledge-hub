import { apiClient } from './client'
import type {
  AgentTask,
  AgentTaskCreate,
  AgentTaskListResponse,
} from '../types/agent'
import type { Note } from '../types/note'

interface AgentTaskListParams {
  page?: number
  page_size?: number
  knowledge_base_id?: number
}

export async function listAgentTasks(
  params: AgentTaskListParams = {},
): Promise<AgentTaskListResponse> {
  const response = await apiClient.get<AgentTaskListResponse>(
    '/agent/tasks',
    { params },
  )
  return response.data
}

export async function getAgentTask(taskId: number): Promise<AgentTask> {
  const response = await apiClient.get<AgentTask>(`/agent/tasks/${taskId}`)
  return response.data
}

export async function createAgentTask(
  data: AgentTaskCreate,
): Promise<AgentTask> {
  const response = await apiClient.post<AgentTask>('/agent/tasks', data, {
    timeout: 210_000,
  })
  return response.data
}

export async function retryAgentTask(taskId: number): Promise<AgentTask> {
  const response = await apiClient.post<AgentTask>(
    `/agent/tasks/${taskId}/retry`,
    undefined,
    { timeout: 210_000 },
  )
  return response.data
}

export async function saveAgentTaskAsNote(taskId: number): Promise<Note> {
  const response = await apiClient.post<Note>(
    `/agent/tasks/${taskId}/save-note`,
  )
  return response.data
}
