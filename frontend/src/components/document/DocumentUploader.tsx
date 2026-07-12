import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'

const ALLOWED_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx']
const MAX_FILE_SIZE = 20 * 1024 * 1024

interface DocumentUploaderProps {
  isUploading: boolean
  progress: number
  error: string | null
  onUpload: (file: File) => Promise<void>
}

export function DocumentUploader({
  isUploading,
  progress,
  error,
  onUpload,
}: DocumentUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  async function selectFile(file: File | undefined) {
    if (!file || isUploading) return
    const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setValidationError('只支持 TXT、Markdown、PDF 和 DOCX 文件')
      return
    }
    if (file.size === 0) {
      setValidationError('不能上传空文件')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      setValidationError('单个文件不能超过 20MB')
      return
    }

    setValidationError(null)
    await onUpload(file)
    if (inputRef.current) inputRef.current.value = ''
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    void selectFile(event.target.files?.[0])
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    void selectFile(event.dataTransfer.files[0])
  }

  return (
    <div>
      <div
        onDragEnter={(event) => {
          event.preventDefault()
          if (!isUploading) setIsDragging(true)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${
          isDragging
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-300 bg-slate-50'
        }`}
      >
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-white text-sm font-bold text-indigo-600 shadow-sm">
          ↑
        </div>
        <p className="mt-3 text-sm font-medium text-slate-700">
          拖拽文件到这里，或选择本地文件
        </p>
        <p className="mt-1 text-xs text-slate-400">
          支持 .txt、.md、.pdf、.docx，单个文件最大 20MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.md,.pdf,.docx"
          disabled={isUploading}
          onChange={handleChange}
          className="hidden"
        />
        <button
          type="button"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isUploading ? '正在上传…' : '选择文件'}
        </button>

        {isUploading && (
          <div className="mx-auto mt-4 max-w-sm">
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-slate-500">上传进度 {progress}%</p>
          </div>
        )}
      </div>

      {(validationError || error) && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {validationError || error}
        </p>
      )}
    </div>
  )
}
