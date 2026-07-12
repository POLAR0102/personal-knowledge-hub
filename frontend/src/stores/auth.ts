import { create } from 'zustand'
import { getCurrentUser, loginUser } from '../api/auth'
import type { AuthUser, LoginRequest } from '../types/auth'
import {
  getAccessToken,
  removeAccessToken,
  saveAccessToken,
  setUnauthorizedHandler,
} from '../utils/auth-session'

interface AuthState {
  accessToken: string | null
  user: AuthUser | null
  isInitializing: boolean
  login: (credentials: LoginRequest) => Promise<void>
  restoreSession: () => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: getAccessToken(),
  user: null,
  isInitializing: true,

  login: async (credentials) => {
    const response = await loginUser(credentials)
    saveAccessToken(response.access_token)
    set({ accessToken: response.access_token, user: response.user })
  },

  restoreSession: async () => {
    const accessToken = getAccessToken()
    if (!accessToken) {
      set({ accessToken: null, user: null, isInitializing: false })
      return
    }

    try {
      const user = await getCurrentUser()
      set({ accessToken, user, isInitializing: false })
    } catch {
      removeAccessToken()
      set({ accessToken: null, user: null, isInitializing: false })
    }
  },

  logout: () => {
    removeAccessToken()
    set({ accessToken: null, user: null, isInitializing: false })
  },
}))

setUnauthorizedHandler(() => {
  useAuthStore.getState().logout()
  if (!['/login', '/register'].includes(window.location.pathname)) {
    window.location.replace('/login')
  }
})
