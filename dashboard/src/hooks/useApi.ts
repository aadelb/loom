import { useQuery, useMutation, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { apiClient, ApiError } from '../api/client'

export function useTools(): UseQueryResult<unknown, ApiError> {
  return useQuery({
    queryKey: ['tools'],
    queryFn: () => apiClient.getTools(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useAnalytics(timeRange: string = '24h'): UseQueryResult<unknown, ApiError> {
  return useQuery({
    queryKey: ['analytics', timeRange],
    queryFn: () => apiClient.getAnalytics(timeRange),
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  })
}

export function useHealth(): UseQueryResult<unknown, ApiError> {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  })
}

export function useHealthDeep(): UseQueryResult<unknown, ApiError> {
  return useQuery({
    queryKey: ['health', 'deep'],
    queryFn: () => apiClient.getHealthDeep(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  })
}

export function useExecuteTool(): UseMutationResult<unknown, ApiError, { toolName: string; params: Record<string, unknown> }> {
  return useMutation({
    mutationFn: ({ toolName, params }) => apiClient.executeTool(toolName, params),
  })
}
