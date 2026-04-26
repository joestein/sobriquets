import type {
  ChatEvent,
  SearchRequest,
  SearchResult,
  Topic,
  PageInfo,
} from "./types";

const API_BASE = "/api";

export async function* chatStream(
  message: string,
  sessionId: string | null
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        // Event type is embedded in the JSON data, skip the SSE event line
        continue;
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        try {
          const event: ChatEvent = JSON.parse(data);
          yield event;
        } catch {
          // Skip malformed events
        }
      }
    }
  }
}

export async function search(
  query: string,
  topK: number = 5,
  topic?: string
): Promise<SearchResult[]> {
  const body: SearchRequest = { query, top_k: topK };
  if (topic) body.topic = topic;

  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Search request failed: ${response.status}`);
  }

  const data = await response.json();
  return data.results;
}

export async function getTopics(): Promise<Topic[]> {
  const response = await fetch(`${API_BASE}/topics`);
  if (!response.ok) {
    throw new Error(`Topics request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.topics;
}

export async function getPages(topic: string): Promise<PageInfo[]> {
  const response = await fetch(`${API_BASE}/pages/${encodeURIComponent(topic)}`);
  if (!response.ok) {
    throw new Error(`Pages request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.pages;
}
