export interface SemanticSearchRequest {
  knowledge_base_id: number
  query: string
  top_k?: number
}

export interface SemanticSearchResult {
  chunk_id: number
  document_id: number
  filename: string
  content: string
  chunk_index: number
  page_number: number | null
  section_title: string | null
  distance: number
}

export interface SemanticSearchResponse {
  query: string
  knowledge_base_id: number
  results: SemanticSearchResult[]
}
