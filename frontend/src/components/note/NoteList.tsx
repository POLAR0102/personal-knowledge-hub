import type { Note } from '../../types/note'
import { formatDateTime } from '../../utils/date'

interface NoteListProps {
  notes: Note[]
  activeNoteId: number | null
  isLoading: boolean
  error: string | null
  onSelect: (noteId: number) => void
  onRetry: () => void
}

export function NoteList({
  notes,
  activeNoteId,
  isLoading,
  error,
  onSelect,
  onRetry,
}: NoteListProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-20 text-center text-sm text-slate-400 shadow-sm">
        正在加载笔记…
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-16 text-center">
        <p className="text-sm text-rose-700">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700"
        >
          重新加载
        </button>
      </div>
    )
  }

  if (notes.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-20 text-center text-sm text-slate-400 shadow-sm">
        当前筛选条件下还没有笔记。
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {notes.map((note) => (
        <button
          key={note.id}
          type="button"
          onClick={() => onSelect(note.id)}
          className={`w-full rounded-2xl border p-4 text-left shadow-sm transition ${
            note.id === activeNoteId
              ? 'border-indigo-200 bg-indigo-50'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
        >
          <span className="flex items-start justify-between gap-3">
            <span className="min-w-0">
              <span className="block truncate font-semibold text-slate-800">{note.title}</span>
              <span className="mt-1 block line-clamp-2 text-xs leading-5 text-slate-500">
                {note.content}
              </span>
            </span>
            <span
              className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${
                note.source_type === 'agent'
                  ? 'bg-violet-50 text-violet-700'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {note.source_type === 'agent' ? 'Agent 生成' : '手动创建'}
            </span>
          </span>
          <span className="mt-3 block text-xs text-slate-400">
            更新于 {formatDateTime(note.updated_at)}
          </span>
        </button>
      ))}
    </div>
  )
}
