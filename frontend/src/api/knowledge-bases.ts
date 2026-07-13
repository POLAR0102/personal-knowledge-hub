import { apiClient } from './client'
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseListResponse,
  KnowledgeBaseReindexResponse,
  KnowledgeBaseUpdate,
} from '../types/knowledge-base'

interface KnowledgeBaseListParams {
  page?: number
  page_size?: number
}

export async function listKnowledgeBases(
  params: KnowledgeBaseListParams = {},
): Promise<KnowledgeBaseListResponse> {
  const response = await apiClient.get<KnowledgeBaseListResponse>(
    '/knowledge-bases',
    { params },
  )
  return response.data
}

export async function getKnowledgeBase(id: number): Promise<KnowledgeBase> {
  const response = await apiClient.get<KnowledgeBase>(`/knowledge-bases/${id}`)
  return response.data
}

export async function createKnowledgeBase(
  data: KnowledgeBaseCreate,
): Promise<KnowledgeBase> {
  const response = await apiClient.post<KnowledgeBase>('/knowledge-bases', data)
  return response.data
}

export async function updateKnowledgeBase(
  id: number,
  data: KnowledgeBaseUpdate,
): Promise<KnowledgeBase> {
  const response = await apiClient.put<KnowledgeBase>(
    `/knowledge-bases/${id}`,
    data,
  )
  return response.data
}

export async function deleteKnowledgeBase(id: number): Promise<void> {
  await apiClient.delete(`/knowledge-bases/${id}`)
}

export async function reindexKnowledgeBase(
  id: number,
): Promise<KnowledgeBaseReindexResponse> {
  const response = await apiClient.post<KnowledgeBaseReindexResponse>(
    `/knowledge-bases/${id}/reindex`,
    undefined,
    { timeout: 120_000 },
  )
  return response.data
}
