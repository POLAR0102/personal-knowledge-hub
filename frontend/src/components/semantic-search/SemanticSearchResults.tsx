import type { SemanticSearchResult } from '../../types/semantic-search'

interface SemanticSearchResultsProps {
  results: SemanticSearchResult[]
}

export function SemanticSearchResults({ results }: SemanticSearchResultsProps) {
  if (results.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-sm text-slate-500">
        当前知识库暂无匹配的已索引片段
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {results.map((result, index) => (
        <article key={result.chunk_id} className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="rounded-full bg-indigo-50 px-2 py-1 font-semibold text-indigo-700">
              结果 {index + 1}
            </span>
            <span className="font-medium text-slate-700">{result.filename}</span>
            <span>Chunk #{result.chunk_index}</span>
            {result.page_number !== null && <span>第 {result.page_number} 页</span>}
            {result.section_title && <span>章节：{result.section_title}</span>}
          </div>
          <pre className="mt-4 whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-700">
            {result.content}
          </pre>
          <p className="mt-4 text-xs text-slate-400">
            cosine distance：{result.distance.toFixed(4)}（越小通常越相关）
          </p>
        </article>
      ))}
    </div>
  )
}
