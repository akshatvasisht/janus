import { useEffect, useRef } from 'react';

/**
 * Returns a debounced callback to rate-limit invocation frequency.
 *
 * @param callback - Function to debounce.
 * @param delay - Delay in milliseconds before invoking the callback.
 * @returns Debounced function with the same signature as the original callback.
 */
export function useDebounce<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const callbackRef = useRef(callback);

  // Track latest callback without resetting the debounce timer.
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
