import axios from 'axios'

interface ValidationErrorItem {
  msg?: string
}

interface ErrorResponse {
  detail?: string | ValidationErrorItem[]
}

export function getApiErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (!axios.isAxiosError<ErrorResponse>(error)) {
    return fallback
  }

  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    const messages: Record<string, string> = {
      'Email is already registered': '该邮箱已经注册',
      'Incorrect email or password': '邮箱或密码错误',
      'Unable to register user': '注册失败，请稍后重试',
      'Unable to authenticate user': '登录失败，请稍后重试',
      'Knowledge base not found': '知识库不存在或无权访问',
      'Knowledge base operation failed': '知识库操作失败，请稍后重试',
      'Document not found': '文档不存在或无权访问',
      'Document operation failed': '文档操作失败，请稍后重试',
      'Document storage operation failed': '文档文件操作失败，请稍后重试',
      'Invalid filename': '文件名无效',
      'File is empty': '不能上传空文件',
      'File is too large': '文件超过上传大小限制',
      'Unsupported file type or MIME type': '文件格式或 MIME 类型不受支持',
      'Document is already processing': '文档正在处理中，请勿重复提交',
      'Document is currently indexing': '文档正在建立索引，请勿重复操作',
      'Document is already indexing': '文档正在建立索引，请勿重复提交',
      'Document must be processed before indexing': '请先完成文档解析，再建立索引',
      'Document has no chunks to index': '文档没有可建立索引的文本片段',
      'Embedding service is not configured': 'Embedding 服务尚未配置',
      'Vector store is not available': '向量数据库暂时不可用',
      'Unable to delete document vectors': '文档向量清理失败，已取消删除',
      'Unable to delete knowledge base vectors': '知识库向量清理失败，已取消删除',
    }
    return messages[detail] ?? detail
  }
  if (Array.isArray(detail) && detail[0]?.msg) {
    return detail[0].msg
  }
  if (!error.response) {
    return '无法连接后端服务，请稍后重试'
  }
  return fallback
}
