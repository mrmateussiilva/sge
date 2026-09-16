import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { MeResponse } from '@/types'

export function useAuth() {
  const query = useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<MeResponse>('/api/v1/me/'),
    staleTime: 1000 * 60 * 2, // 2 minutos
    retry: 1,
  })

  return {
    user: query.data?.user,
    alertas: query.data?.alertas,
    app: query.data?.app,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}
