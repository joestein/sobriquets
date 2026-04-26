import { useState } from "react";
import type { SourceRef } from "../api/types";

interface SourceCitationProps {
  source: SourceRef;
}

export default function SourceCitation({ source }: SourceCitationProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="inline-flex flex-col items-start text-left rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm hover:bg-blue-100 transition-colors"
    >
      <div className="flex items-center gap-1.5">
        <svg
          className={`h-3 w-3 text-blue-500 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span className="font-medium text-blue-700">{source.title}</span>
        {source.relevance_score > 0 && (
          <span className="text-xs text-blue-400">
            {(source.relevance_score * 100).toFixed(0)}%
          </span>
        )}
      </div>
      {expanded && (
        <div className="mt-1 text-xs text-blue-600 pl-4">
          <div>Path: {source.file_path}</div>
          {source.heading && <div>Section: {source.heading}</div>}
        </div>
      )}
    </button>
  );
}
