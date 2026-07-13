export type NoteSourceType = 'manual' | 'agent'

export interface Note {
  id: number
  user_id: number
  knowledge_base_id: number
  title: string
  content: string
  source_type: NoteSourceType
  source_agent_task_id: number | null
  created_at: string
  updated_at: string
}

export interface NoteCreate {
  knowledge_base_id: number
  title: string
  content: string
}

export interface NoteUpdate {
  title?: string
  content?: string
}

export interface NoteListResponse {
  items: Note[]
  total: number
  page: number
  page_size: number
}
