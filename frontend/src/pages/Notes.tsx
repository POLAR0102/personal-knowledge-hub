import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listKnowledgeBases } from '../api/knowledge-bases'
import {
  createNote,
  deleteNote,
  getNote,
  listNotes,
  updateNote,
} from '../api/notes'
import { DeleteNoteDialog } from '../components/note/DeleteNoteDialog'
import { NoteDetail } from '../components/note/NoteDetail'
import { NoteFormDialog } from '../components/note/NoteFormDialog'
import { NoteList } from '../components/note/NoteList'
import type { KnowledgeBase } from '../types/knowledge-base'
import type { Note, NoteCreate } from '../types/note'
import { getApiErrorMessage } from '../utils/api-error'

const PAGE_SIZE = 10

export function Notes() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [knowledgeBaseError, setKnowledgeBaseError] = useState<string | null>(null)
  const [knowledgeBaseFilter, setKnowledgeBaseFilter] = useState<number | null>(null)
  const [notes, setNotes] = useState<Note[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoadingNotes, setIsLoadingNotes] = useState(true)
  const [noteListError, setNoteListError] = useState<string | null>(null)
  const [activeNoteId, setActiveNoteId] = useState<number | null>(null)
  const [activeNote, setActiveNote] = useState<Note | null>(null)
  const [isLoadingNote, setIsLoadingNote] = useState(false)
  const [noteLoadError, setNoteLoadError] = useState<string | null>(null)
  const noteRequestId = useRef(0)
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deletingNote, setDeletingNote] = useState<Note | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadNotes = useCallback(async () => {
    setIsLoadingNotes(true)
    setNoteListError(null)
    try {
      const data = await listNotes({
        page,
        page_size: PAGE_SIZE,
        ...(knowledgeBaseFilter !== null && {
          knowledge_base_id: knowledgeBaseFilter,
        }),
      })
      setNotes(data.items)
      setTotal(data.total)
    } catch (error: unknown) {
      setNoteListError(getApiErrorMessage(error, '笔记列表加载失败，请稍后重试'))
    } finally {
      setIsLoadingNotes(false)
    }
  }, [knowledgeBaseFilter, page])

  useEffect(() => {
    void loadNotes()
  }, [loadNotes])

  useEffect(() => {
    listKnowledgeBases({ page: 1, page_size: 100 })
      .then((data) => setKnowledgeBases(data.items))
      .catch((error: unknown) => {
        setKnowledgeBaseError(
          getApiErrorMessage(error, '知识库加载失败，请稍后重试'),
        )
      })
  }, [])

  useEffect(() => {
    if (isLoadingNotes || noteListError) return
    const requestedId = Number(searchParams.get('note'))
    const requestedNote = notes.find((note) => note.id === requestedId)
    const nextId = requestedNote?.id ?? notes[0]?.id ?? null
    setActiveNoteId(nextId)
    if (nextId !== null && requestedId !== nextId) {
      setSearchParams({ note: String(nextId) }, { replace: true })
    } else if (nextId === null && searchParams.has('note')) {
      setSearchParams({}, { replace: true })
    }
  }, [isLoadingNotes, noteListError, notes, searchParams, setSearchParams])

  const loadNote = useCallback(async (noteId: number) => {
    const requestId = ++noteRequestId.current
    setIsLoadingNote(true)
    setNoteLoadError(null)
    try {
      const data = await getNote(noteId)
      if (requestId !== noteRequestId.current) return
      setActiveNote(data)
    } catch (error: unknown) {
      if (requestId !== noteRequestId.current) return
      setActiveNote(null)
      setNoteLoadError(getApiErrorMessage(error, '笔记详情加载失败，请稍后重试'))
    } finally {
      if (requestId === noteRequestId.current) {
        setIsLoadingNote(false)
      }
    }
  }, [])

  useEffect(() => {
    setActionError(null)
    if (activeNoteId === null) {
      noteRequestId.current += 1
      setActiveNote(null)
      setNoteLoadError(null)
      return
    }
    void loadNote(activeNoteId)
  }, [activeNoteId, loadNote])

  async function handleFormSubmit(data: NoteCreate) {
    if (isSubmitting) return
    setIsSubmitting(true)
    setActionError(null)
    try {
      if (formMode === 'edit' && activeNote) {
        const updated = await updateNote(activeNote.id, {
          title: data.title,
          content: data.content,
        })
        setActiveNote(updated)
        setNotes((current) => [
          updated,
          ...current.filter((note) => note.id !== updated.id),
        ])
        setSearchParams({ note: String(updated.id) })
        if (page === 1) {
          await loadNotes()
        } else {
          setPage(1)
          setNotes([updated])
        }
      } else {
        const created = await createNote(data)
        const needsExplicitReload =
          knowledgeBaseFilter === created.knowledge_base_id && page === 1
        setKnowledgeBaseFilter(created.knowledge_base_id)
        setPage(1)
        setNotes([created])
        setTotal(1)
        setActiveNote(created)
        setSearchParams({ note: String(created.id) })
        if (needsExplicitReload) await loadNotes()
      }
      setFormMode(null)
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '笔记保存失败，请稍后重试'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!deletingNote || isDeleting) return
    setIsDeleting(true)
    setActionError(null)
    try {
      await deleteNote(deletingNote.id)
      const remaining = notes.filter((note) => note.id !== deletingNote.id)
      setNotes(remaining)
      setTotal((current) => Math.max(0, current - 1))
      setDeletingNote(null)
      if (deletingNote.id === activeNoteId) {
        const nextId = remaining[0]?.id
        setSearchParams(nextId ? { note: String(nextId) } : {})
      }
      if (remaining.length === 0 && page > 1) {
        setPage((current) => current - 1)
      } else {
        await loadNotes()
      }
    } catch (error: unknown) {
      setActionError(getApiErrorMessage(error, '笔记删除失败，请稍后重试'))
    } finally {
      setIsDeleting(false)
    }
  }

  const activeKnowledgeBase = useMemo(
    () =>
      knowledgeBases.find(
        (knowledgeBase) => knowledgeBase.id === activeNote?.knowledge_base_id,
      ) ?? null,
    [activeNote?.knowledge_base_id, knowledgeBases],
  )
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-5 rounded-2xl bg-gradient-to-r from-slate-950 to-emerald-950 p-6 text-white shadow-sm sm:p-8 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-emerald-300">阶段 F · Markdown 笔记</p>
          <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">个人笔记</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
            管理手动记录和由 Agent 结果保存而来的 Markdown 笔记。
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setActionError(null)
            setFormMode('create')
          }}
          className="w-fit rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-100"
        >
          + 创建笔记
        </button>
      </section>

      {knowledgeBaseError && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {knowledgeBaseError}
        </p>
      )}

      <section className="flex flex-col justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
        <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
          知识库筛选
          <select
            value={knowledgeBaseFilter ?? ''}
            onChange={(event) => {
              setKnowledgeBaseFilter(
                event.target.value ? Number(event.target.value) : null,
              )
              setPage(1)
            }}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
          >
            <option value="">全部知识库</option>
            {knowledgeBases.map((knowledgeBase) => (
              <option key={knowledgeBase.id} value={knowledgeBase.id}>
                {knowledgeBase.name}
              </option>
            ))}
          </select>
        </label>
        <span className="text-sm text-slate-400">共 {total} 篇笔记</span>
      </section>

      <section className="grid items-start gap-5 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <div className="space-y-4">
          <NoteList
            notes={notes}
            activeNoteId={activeNoteId}
            isLoading={isLoadingNotes}
            error={noteListError}
            onSelect={(noteId) => setSearchParams({ note: String(noteId) })}
            onRetry={() => void loadNotes()}
          />

          {!isLoadingNotes && !noteListError && total > 0 && (
            <nav className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
              <span className="text-slate-400">{page}/{totalPages} 页</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => current - 1)}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-slate-600 disabled:opacity-40"
                >
                  上一页
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((current) => current + 1)}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-slate-600 disabled:opacity-40"
                >
                  下一页
                </button>
              </div>
            </nav>
          )}
        </div>

        <NoteDetail
          note={activeNote}
          knowledgeBase={activeKnowledgeBase}
          isLoading={isLoadingNote}
          error={noteLoadError}
          onEdit={() => {
            setActionError(null)
            setFormMode('edit')
          }}
          onDelete={() => {
            setActionError(null)
            setDeletingNote(activeNote)
          }}
          onRetry={() => {
            if (activeNoteId !== null) void loadNote(activeNoteId)
          }}
        />
      </section>

      {formMode && (
        <NoteFormDialog
          key={formMode === 'edit' ? activeNote?.id : 'create'}
          mode={formMode}
          knowledgeBases={knowledgeBases}
          initialValue={formMode === 'edit' ? activeNote ?? undefined : undefined}
          defaultKnowledgeBaseId={knowledgeBaseFilter ?? undefined}
          isSubmitting={isSubmitting}
          error={actionError}
          onSubmit={handleFormSubmit}
          onCancel={() => {
            setFormMode(null)
            setActionError(null)
          }}
        />
      )}

      {deletingNote && (
        <DeleteNoteDialog
          note={deletingNote}
          isDeleting={isDeleting}
          error={actionError}
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            setDeletingNote(null)
            setActionError(null)
          }}
        />
      )}
    </div>
  )
}
