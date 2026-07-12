import { useEffect } from 'react'
import { AppRoutes } from './routes'
import { useAuthStore } from './stores/auth'

function App() {
  const restoreSession = useAuthStore((state) => state.restoreSession)

  useEffect(() => {
    void restoreSession()
  }, [restoreSession])

  return <AppRoutes />
}

export default App
