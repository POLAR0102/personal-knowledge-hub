import type { AxiosProgressEvent } from 'axios'
import { apiClient } from './client'
import type {
  DocumentListResponse,
  DocumentChunkListResponse,
  DocumentIndexResult,
  DocumentIndexStatusResponse,
  DocumentProcessResult,
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

export async function processDocument(id: number): Promise<DocumentProcessResult> {
  const response = await apiClient.post<DocumentProcessResult>(
    `/documents/${id}/process`,
  )
  return response.data
}

export async function indexDocument(id: number): Promise<DocumentIndexResult> {
  const response = await apiClient.post<DocumentIndexResult>(
    `/documents/${id}/index`,
    undefined,
    { timeout: 60_000 },
  )
  return response.data
}

export async function getDocumentIndexStatus(
  id: number,
): Promise<DocumentIndexStatusResponse> {
  const response = await apiClient.get<DocumentIndexStatusResponse>(
    `/documents/${id}/index-status`,
    { timeout: 30_000 },
  )
  return response.data
}

export async function listDocumentChunks(
  id: number,
  params: { page?: number; page_size?: number } = {},
): Promise<DocumentChunkListResponse> {
  const response = await apiClient.get<DocumentChunkListResponse>(
    `/documents/${id}/chunks`,
    { params },
  )
  return response.data
}
