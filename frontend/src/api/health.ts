import type { AxiosRequestConfig } from 'axios'
import type { HealthResponse } from '../types/health'
import { apiClient } from './client'

export async function getHealth(
  config?: AxiosRequestConfig,
): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health', config)
  return response.data
}
