'use client';

import { useQuery } from '@tanstack/react-query';

const API_URL = 'http://localhost:8000';

/**
 * Hook for checking backend health status.
 * 
 * Periodically polls the backend health endpoint to verify service availability.
 * Automatically retries failed requests and refetches every 30 seconds.
 * 
 * @returns React Query result object containing health check status and data.
 */
export function useBackendHealth() {
  return useQuery({
    queryKey: ['backend', 'health'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/health`);
      if (!response.ok) throw new Error('Health check failed');
      return response.json();
    },
    refetchInterval: 30000, // Check every 30 seconds
    retry: 3,
  });
}
