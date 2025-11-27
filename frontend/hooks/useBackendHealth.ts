'use client';

import { useQuery } from '@tanstack/react-query';
import type { HealthResponse } from '@/types/janus';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Hook for checking backend health status.
 *
 * Periodically polls the backend health endpoint to verify service availability.
 * Automatically retries failed requests and refetches every 30 seconds.
 *
 * @returns React Query result object containing health check status and data.
 */
export function useBackendHealth() {
  return useQuery<HealthResponse, Error>({
    queryKey: ['backend', 'health'],
    queryFn: async (): Promise<HealthResponse> => {
      const response = await fetch(`${API_URL}/api/health`);
      if (!response.ok) throw new Error('Health check failed');
      return response.json() as Promise<HealthResponse>;
    },
    refetchInterval: 30000,
    retry: 3,
  });
}
