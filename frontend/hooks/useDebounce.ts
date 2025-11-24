import { useEffect, useRef } from 'react';

/**
 * Custom hook for debouncing function calls.
 * 
 * Returns a debounced version of the callback function that delays execution
 * until after the specified delay period has elapsed since the last invocation.
 * 
 * @param callback - The function to debounce.
 * @param delay - Delay in milliseconds before executing the callback.
 * @returns Debounced function with the same signature as the original callback.
 */
export function useDebounce<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const callbackRef = useRef(callback);

  // Update callback ref when it changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const debouncedCallback = ((...args: Parameters<T>) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      callbackRef.current(...args);
    }, delay);
  }) as T;

  return debouncedCallback;
}

