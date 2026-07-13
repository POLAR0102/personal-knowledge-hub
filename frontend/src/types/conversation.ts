import type { RagCitation } from './rag'

export type MessageRole = 'user' | 'assistant'
export type MessageRequestStatus = 'processing' | 'completed' | 'failed'

export interface Conversation {
  id: number
  user_id: number
  knowledge_base_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  conversation_id: number
  role: MessageRole
  content: string
  citations: RagCitation[] | null
  model: string | null
  sequence_number: number
  created_at: string
  client_request_id: string | null
  request_status: MessageRequestStatus | null
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[]
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
  page: number
  page_size: number
}

export interface ConversationCreate {
  knowledge_base_id: number
  title: string
}

export interface ConversationMessageCreate {
  content: string
  top_k?: number
  client_request_id: string
}

export interface ConversationMessageResponse {
  user_message: ConversationMessage
  assistant_message: ConversationMessage
}
