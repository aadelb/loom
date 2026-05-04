import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8787'
const API_KEY = import.meta.env.VITE_API_KEY

export interface ApiError extends AxiosError {
  response?: {
    status: number
    data: {
      error?: string
      message?: string
      details?: string
    }
  }
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(API_KEY && { 'X-API-Key': API_KEY }),
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
        })
        return Promise.reject(error)
      }
    )
  }

  async getTools() {
    const response = await this.client.get('/openapi.json')
    return response.data
  }

  async getAnalytics(timeRange: string = '24h') {
    const response = await this.client.post('/tools/research_analytics_dashboard', {
      time_range: timeRange,
    })
    return response.data
  }

  async getHealth() {
    const response = await this.client.get('/health')
    return response.data
  }

  async getHealthDeep() {
    const response = await this.client.get('/health/deep')
    return response.data
  }

  async executeTool(toolName: string, params: Record<string, unknown>) {
    const response = await this.client.post(`/tools/${toolName}`, params)
    return response.data
  }
}

export const apiClient = new ApiClient()
