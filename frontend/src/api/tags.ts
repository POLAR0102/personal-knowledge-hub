import { apiClient } from './client'
import type {
  Tag,
  TagCreate,
  TagListResponse,
  TagUpdate,
} from '../types/tag'

interface TagListParams {
  page?: number
  page_size?: number
}

export async function listTags(
  params: TagListParams = {},
): Promise<TagListResponse> {
  const response = await apiClient.get<TagListResponse>('/tags', { params })
  return response.data
}

export async function createTag(data: TagCreate): Promise<Tag> {
  const response = await apiClient.post<Tag>('/tags', data)
  return response.data
}

export async function updateTag(tagId: number, data: TagUpdate): Promise<Tag> {
  const response = await apiClient.put<Tag>(`/tags/${tagId}`, data)
  return response.data
}

export async function deleteTag(tagId: number): Promise<void> {
  await apiClient.delete(`/tags/${tagId}`)
}
