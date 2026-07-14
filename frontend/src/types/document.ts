import type { TagSummary } from './tag'

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type DocumentIndexStatus = 'not_indexed' | 'indexing' | 'indexed' | 'failed'

export interface KnowledgeDocument {
  id: number
  user_id: number
  knowledge_base_id: number
  original_filename: string
  file_type: string
  mime_type: string
  file_size: number
  status: DocumentStatus
  error_message: string | null
  index_status: DocumentIndexStatus
  index_error_message: string | null
  indexed_at: string | null
  embedding_model: string | null
  created_at: string
  updated_at: string
  chunk_count: number
  is_favorite: boolean
  tags: TagSummary[]
}

export interface DocumentListResponse {
  items: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
}

export interface DocumentStats {
  total: number
}

export interface DocumentProcessResult {
  document_id: number
  status: DocumentStatus
  chunk_count: number
  updated_at: string
}

export interface DocumentIndexResult {
  document_id: number
  index_status: DocumentIndexStatus
  chunk_count: number
  vector_count: number
  embedding_model: string
  indexed_at: string
}

export interface DocumentIndexStatusResponse {
  document_id: number
  processing_status: DocumentStatus
  index_status: DocumentIndexStatus
  chunk_count: number
  vector_count: number
  embedding_model: string | null
  indexed_at: string | null
  index_error_message: string | null
}

export type IndexHealthStatus =
  | 'healthy'
  | 'missing_vectors'
  | 'extra_vectors'
  | 'model_mismatch'
  | 'not_indexed'
  | 'failed'

export interface DocumentIndexHealthResponse {
  document_id: number
  index_status: DocumentIndexStatus
  health_status: IndexHealthStatus
  chunk_count: number
  vector_count: number
  embedding_model: string | null
  current_embedding_model: string
  indexed_at: string | null
  index_error_message: string | null
}

export interface DocumentChunk {
  id: number
  document_id: number
  chunk_index: number
  content: string
  content_hash: string
  character_count: number
  page_number: number | null
  section_title: string | null
  start_offset: number | null
  end_offset: number | null
  created_at: string
  updated_at: string
}

export interface DocumentChunkListResponse {
  items: DocumentChunk[]
  total: number
  page: number
  page_size: number
}
