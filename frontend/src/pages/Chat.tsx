import { PagePlaceholder } from '../components/PagePlaceholder'

export function Chat() {
  return (
    <PagePlaceholder
      eyebrow="问"
      title="AI 问答"
      description="在这里选择知识库并进行带引用来源的 RAG 问答。当前阶段不调用任何大语言模型。"
    />
  )
}
