import type { Message } from "../api/types";
import SourceCitation from "./SourceCitation";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-white text-gray-800 border border-gray-200 shadow-sm"
        }`}
      >
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
          {!message.content && message.role === "assistant" && (
            <span className="inline-block animate-pulse text-gray-400">
              Thinking...
            </span>
          )}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-gray-100 pt-2">
            {message.sources.map((source, idx) => (
              <SourceCitation key={idx} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
