import { apiClient } from './client'
import type {
  SemanticSearchRequest,
  SemanticSearchResponse,
} from '../types/semantic-search'
import type { RagQueryRequest, RagQueryResponse } from '../types/rag'

export async function semanticSearch(
  data: SemanticSearchRequest,
): Promise<SemanticSearchResponse> {
  const response = await apiClient.post<SemanticSearchResponse>(
    '/rag/search',
    data,
    { timeout: 60_000 },
  )
  return response.data
}

export async function queryKnowledgeBase(
  data: RagQueryRequest,
): Promise<RagQueryResponse> {
  const response = await apiClient.post<RagQueryResponse>('/rag/query', data, {
    timeout: 210_000,
  })
  return response.data
}
