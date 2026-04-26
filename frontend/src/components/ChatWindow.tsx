import { useChat } from "../hooks/useChat";
import ChatInput from "./ChatInput";
import MessageList from "./MessageList";

export default function ChatWindow() {
  const { messages, isStreaming, sendMessage, clearMessages } = useChat();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold text-gray-800">Chat</h1>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Clear
          </button>
        )}
      </div>
      <MessageList messages={messages} isStreaming={isStreaming} />
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
