export interface RagQueryRequest {
  knowledge_base_id: number
  question: string
  top_k?: number
}

export interface RagCitation {
  source_number: number
  chunk_id: number
  document_id: number
  filename: string
  content: string
  chunk_index: number
  page_number: number | null
  section_title: string | null
  distance: number
}

export interface RagQueryResponse {
  answer: string
  knowledge_base_id: number
  citations: RagCitation[]
  retrieval_count: number
  model: string
}
