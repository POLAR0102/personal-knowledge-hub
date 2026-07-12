import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { AppLayout } from '../layouts/AppLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { Agent } from '../pages/Agent'
import { Chat } from '../pages/Chat'
import { Dashboard } from '../pages/Dashboard'
import { Documents } from '../pages/Documents'
import { KnowledgeBases } from '../pages/KnowledgeBases'
import { Login } from '../pages/Login'
import { Notes } from '../pages/Notes'
import { Register } from '../pages/Register'

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
          <Route path="documents" element={<Documents />} />
          <Route path="chat" element={<Chat />} />
          <Route path="agent" element={<Agent />} />
          <Route path="notes" element={<Notes />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
