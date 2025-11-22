'use client';

import { useQuery } from '@tanstack/react-query';

const API_URL = 'http://localhost:8000';

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
