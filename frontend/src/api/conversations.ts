import { apiClient } from './client'
import type {
  Conversation,
  ConversationCreate,
  ConversationDetail,
  ConversationListResponse,
  ConversationMessageCreate,
  ConversationMessageResponse,
} from '../types/conversation'

interface ConversationListParams {
  page?: number
  page_size?: number
}

export async function listConversations(
  params: ConversationListParams = {},
): Promise<ConversationListResponse> {
  const response = await apiClient.get<ConversationListResponse>(
    '/conversations',
    { params },
  )
  return response.data
}

export async function createConversation(
  data: ConversationCreate,
): Promise<Conversation> {
  const response = await apiClient.post<Conversation>('/conversations', data)
  return response.data
}

export async function getConversation(
  conversationId: number,
): Promise<ConversationDetail> {
  const response = await apiClient.get<ConversationDetail>(
    `/conversations/${conversationId}`,
  )
  return response.data
}

export async function deleteConversation(
  conversationId: number,
): Promise<void> {
  await apiClient.delete(`/conversations/${conversationId}`)
}

export async function sendConversationMessage(
  conversationId: number,
  data: ConversationMessageCreate,
): Promise<ConversationMessageResponse> {
  const response = await apiClient.post<ConversationMessageResponse>(
    `/conversations/${conversationId}/messages`,
    data,
    { timeout: 210_000 },
  )
  return response.data
}
