"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Lightweight data-fetching hook with manual refresh + optional polling.
 * (Kept dependency-free; swap for SWR/React Query if preferred.)
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = [], intervalMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    if (intervalMs) {
      const timer = setInterval(load, intervalMs);
      return () => clearInterval(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs]);

  return { data, error, loading, refresh: load };
}
