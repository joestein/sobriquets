import { useCallback, useRef, useState } from "react";
import { chatStream } from "../api/client";
import type { Message } from "../api/types";

function generateId(): string {
  return crypto.randomUUID();
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      // Initialize session ID on first message
      if (!sessionIdRef.current) {
        sessionIdRef.current = generateId();
      }

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: content.trim(),
      };

      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        sources: [],
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      try {
        const stream = chatStream(content.trim(), sessionIdRef.current);

        for await (const event of stream) {
          switch (event.type) {
            case "token":
              if (event.content) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last.role === "assistant") {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + event.content,
                    };
                  }
                  return updated;
                });
              }
              break;

            case "source":
              if (event.sources) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last.role === "assistant") {
                    updated[updated.length - 1] = {
                      ...last,
                      sources: [
                        ...(last.sources || []),
                        ...event.sources!,
                      ],
                    };
                  }
                  return updated;
                });
              }
              break;

            case "error":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content:
                      event.content ||
                      "An error occurred. Please try again.",
                  };
                }
                return updated;
              });
              break;

            case "done":
              break;
          }
        }
      } catch (error) {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: "Failed to connect to the server. Please check that the backend is running.",
            };
          }
          return updated;
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = null;
  }, []);

  return { messages, isStreaming, sendMessage, clearMessages };
}
