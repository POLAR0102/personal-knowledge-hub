export interface HealthResponse {
  status: string
  service: string
}

export type ApiConnectionStatus = 'checking' | 'online' | 'offline'
