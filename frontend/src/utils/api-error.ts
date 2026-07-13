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
