import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { AppLayout } from '../layouts/AppLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { Chat } from '../pages/Chat'
import { Dashboard } from '../pages/Dashboard'
import { KnowledgeBaseDetail } from '../pages/KnowledgeBaseDetail'
import { KnowledgeBases } from '../pages/KnowledgeBases'
import { Login } from '../pages/Login'
import { Register } from '../pages/Register'

const Agent = lazy(() =>
  import('../pages/Agent').then((module) => ({ default: module.Agent })),
)
const Notes = lazy(() =>
  import('../pages/Notes').then((module) => ({ default: module.Notes })),
)
const Documents = lazy(() =>
  import('../pages/Documents').then((module) => ({ default: module.Documents })),
)
const Favorites = lazy(() =>
  import('../pages/Favorites').then((module) => ({ default: module.Favorites })),
)
const SemanticSearch = lazy(() =>
  import('../pages/SemanticSearch').then((module) => ({
    default: module.SemanticSearch,
  })),
)

const pageFallback = (
  <div className="rounded-2xl border border-slate-200 bg-white px-6 py-20 text-center text-sm text-slate-400 shadow-sm">
    正在加载页面…
  </div>
)

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="knowledge-bases" element={<KnowledgeBases />} />
          <Route
            path="knowledge-bases/:id"
            element={<KnowledgeBaseDetail />}
          />
          <Route
            path="documents"
            element={<Suspense fallback={pageFallback}><Documents /></Suspense>}
          />
          <Route
            path="favorites"
            element={<Suspense fallback={pageFallback}><Favorites /></Suspense>}
          />
          <Route
            path="semantic-search"
            element={<Suspense fallback={pageFallback}><SemanticSearch /></Suspense>}
          />
          <Route path="chat" element={<Chat />} />
          <Route
            path="agent"
            element={<Suspense fallback={pageFallback}><Agent /></Suspense>}
          />
          <Route
            path="notes"
            element={<Suspense fallback={pageFallback}><Notes /></Suspense>}
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
