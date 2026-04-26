import { useCallback, useEffect, useState } from "react";
import { getTopics } from "../api/client";
import type { Topic } from "../api/types";

export default function Sidebar() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTopics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTopics();
      setTopics(data);
    } catch {
      setError("Could not load topics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTopics();
  }, [fetchTopics]);

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      <div className="px-4 py-4 border-b border-gray-700">
        <h1 className="text-xl font-bold tracking-tight">Sobriquets</h1>
        <p className="text-xs text-gray-400 mt-1">Personal Knowledge Wiki</p>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
          Topics
        </h3>

        {loading && (
          <div className="text-sm text-gray-500 px-1">Loading...</div>
        )}

        {error && (
          <div className="text-sm text-red-400 px-1">{error}</div>
        )}

        {!loading && !error && topics.length === 0 && (
          <div className="text-sm text-gray-500 px-1">
            No topics yet. Run the /research skill and then ingest to get
            started.
          </div>
        )}

        <ul className="space-y-0.5">
          {topics.map((topic) => (
            <li key={topic.name}>
              <div className="flex items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-gray-800 cursor-pointer transition-colors">
                <span className="truncate">{topic.name}</span>
                <span className="text-xs text-gray-500 ml-2">
                  {topic.page_count}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t border-gray-700 px-4 py-3">
        <button
          onClick={fetchTopics}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Refresh topics
        </button>
      </div>
    </div>
  );
}
