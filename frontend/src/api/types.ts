export interface ChatRequest {
  message: string;
  session_id: string | null;
}

export interface SourceRef {
  title: string;
  file_path: string;
  heading: string | null;
  relevance_score: number;
}

export interface ChatEvent {
  type: "token" | "source" | "done" | "error";
  content?: string;
  sources?: SourceRef[];
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  topic?: string;
}

export interface SearchResult {
  chunk_id: string;
  content: string;
  heading: string | null;
  source_title: string;
  source_path: string;
  topic: string;
  score: number;
}

export interface Topic {
  name: string;
  page_count: number;
}

export interface PageInfo {
  title: string;
  path: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
}
