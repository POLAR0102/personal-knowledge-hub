import { apiClient } from './client'
import type {
  Note,
  NoteCreate,
  NoteListResponse,
  NoteUpdate,
} from '../types/note'

interface NoteListParams {
  page?: number
  page_size?: number
  knowledge_base_id?: number
}

export async function listNotes(
  params: NoteListParams = {},
): Promise<NoteListResponse> {
  const response = await apiClient.get<NoteListResponse>('/notes', { params })
  return response.data
}

export async function getNote(noteId: number): Promise<Note> {
  const response = await apiClient.get<Note>(`/notes/${noteId}`)
  return response.data
}

export async function createNote(data: NoteCreate): Promise<Note> {
  const response = await apiClient.post<Note>('/notes', data)
  return response.data
}

export async function updateNote(
  noteId: number,
  data: NoteUpdate,
): Promise<Note> {
  const response = await apiClient.put<Note>(`/notes/${noteId}`, data)
  return response.data
}

export async function deleteNote(noteId: number): Promise<void> {
  await apiClient.delete(`/notes/${noteId}`)
}
