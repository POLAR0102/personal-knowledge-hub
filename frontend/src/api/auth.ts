import type {
  AuthUser,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
} from '../types/auth'
import { apiClient } from './client'

export async function registerUser(data: RegisterRequest): Promise<AuthUser> {
  const response = await apiClient.post<AuthUser>('/auth/register', data)
  return response.data
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', data)
  return response.data
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await apiClient.get<AuthUser>('/auth/me')
  return response.data
}
