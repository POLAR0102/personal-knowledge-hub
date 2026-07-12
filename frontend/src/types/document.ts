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
