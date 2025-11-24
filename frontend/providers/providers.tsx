'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

/**
 * Providers component that sets up React Query for the application.
 * 
 * Initializes and provides a QueryClient instance to all child components,
 * enabling data fetching, caching, and synchronization capabilities throughout
 * the application.
 * 
 * @param props - Component props.
 * @param props.children - React node containing components that require React Query context.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}