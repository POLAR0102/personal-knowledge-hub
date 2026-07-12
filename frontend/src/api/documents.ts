import type { AxiosProgressEvent } from 'axios'
import { apiClient } from './client'
import type {
  DocumentListResponse,
  DocumentStats,
  DocumentStatus,
  KnowledgeDocument,
} from '../types/document'

interface DocumentListParams {
  page?: number
  page_size?: number
  status?: DocumentStatus
}

export async function uploadDocument(
  knowledgeBaseId: number,
  file: File,
  onUploadProgress?: (event: AxiosProgressEvent) => void,
): Promise<KnowledgeDocument> {
  const data = new FormData()
  data.append('file', file)
  const response = await apiClient.post<KnowledgeDocument>(
    `/knowledge-bases/${knowledgeBaseId}/documents`,
    data,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    },
  )
  return response.data
}

export async function listDocuments(
  knowledgeBaseId: number,
  params: DocumentListParams = {},
): Promise<DocumentListResponse> {
  const response = await apiClient.get<DocumentListResponse>(
    `/knowledge-bases/${knowledgeBaseId}/documents`,
    { params },
  )
  return response.data
}

export async function getDocument(id: number): Promise<KnowledgeDocument> {
  const response = await apiClient.get<KnowledgeDocument>(`/documents/${id}`)
  return response.data
}

export async function deleteDocument(id: number): Promise<void> {
  await apiClient.delete(`/documents/${id}`)
}

export async function getDocumentStats(): Promise<DocumentStats> {
  const response = await apiClient.get<DocumentStats>('/documents/stats')
  return response.data
}
