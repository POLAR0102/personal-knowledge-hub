export interface Tag {
  id: number
  user_id: number
  name: string
  created_at: string
  updated_at: string
}

export interface TagSummary {
  id: number
  name: string
}

export interface TagCreate {
  name: string
}

export interface TagUpdate {
  name: string
}

export interface TagListResponse {
  items: Tag[]
  total: number
  page: number
  page_size: number
}
