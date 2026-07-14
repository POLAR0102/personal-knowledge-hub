import type { NavigationItem } from '../types/navigation'

export const navigationItems: NavigationItem[] = [
  { label: '首页', shortLabel: '首', path: '/' },
  { label: '知识库', shortLabel: '库', path: '/knowledge-bases' },
  { label: '文档', shortLabel: '文', path: '/documents' },
  { label: '收藏', shortLabel: '藏', path: '/favorites' },
  { label: 'AI 问答', shortLabel: '问', path: '/chat' },
  { label: 'Agent', shortLabel: '智', path: '/agent' },
  { label: '笔记', shortLabel: '记', path: '/notes' },
]
