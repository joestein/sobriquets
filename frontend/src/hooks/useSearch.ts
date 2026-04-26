import { useCallback, useState } from "react";
import { search as searchApi } from "../api/client";
import type { SearchResult } from "../api/types";

export function useSearch() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(
    async (query: string, topK: number = 5, topic?: string) => {
      if (!query.trim()) return;

      setIsSearching(true);
      setError(null);

      try {
        const searchResults = await searchApi(query, topK, topic);
        setResults(searchResults);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Search failed"
        );
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    },
    []
  );

  return { results, isSearching, error, search };
}
