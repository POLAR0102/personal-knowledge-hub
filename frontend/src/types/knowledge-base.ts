export interface KnowledgeBase {
  id: number
  user_id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseCreate {
  name: string
  description: string | null
}

export interface KnowledgeBaseUpdate {
  name?: string | null
  description?: string | null
}

export interface KnowledgeBaseListResponse {
  items: KnowledgeBase[]
  total: number
  page: number
  page_size: number
}

export interface KnowledgeBaseReindexItem {
  document_id: number
  original_filename: string
  index_status: 'indexed' | 'failed'
  vector_count: number
  error_message: string | null
}

export interface KnowledgeBaseReindexResponse {
  knowledge_base_id: number
  total: number
  succeeded: number
  failed: number
  items: KnowledgeBaseReindexItem[]
}
