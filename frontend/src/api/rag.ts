import { apiClient } from './client'
import type {
  SemanticSearchRequest,
  SemanticSearchResponse,
} from '../types/semantic-search'

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
