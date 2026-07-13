export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

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
  created_at: string
  updated_at: string
  chunk_count: number
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
