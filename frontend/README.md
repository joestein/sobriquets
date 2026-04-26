# Frontend

React TypeScript chat interface for Sobriquets. Connects to the FastAPI backend via SSE for streaming chat and JSON for search and topic browsing.

## Setup

### With Docker (recommended)

From the repo root:

```bash
make up
# Frontend is available at http://localhost:5173
```

Hot-reload works via the Docker volume mount (`./frontend/src:/app/src`).

### Without Docker

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev
# Available at http://localhost:5173
```

Vite proxies `/api` requests to `http://localhost:8000` (configured in `vite.config.ts`), so the backend must be running.

```bash
# Production build
npm run build    # outputs to dist/
npm run preview  # serve the production build locally
```

## Component Overview

```
App
  Sidebar                  # Topic list with refresh button
  ChatWindow               # Main chat container
    MessageList            # Scrollable message history (auto-scrolls to bottom)
      MessageBubble        # User or assistant message
        SourceCitation     # Expandable source chip (title, path, score)
    ChatInput              # Auto-resizing textarea; send on Enter or Ctrl+Enter
```

### Key Behaviors

- **Streaming**: `useChat` hook consumes SSE from `POST /api/chat`. Tokens are appended to the current assistant message in real-time as they arrive.
- **Source citations**: When a `source` SSE event arrives, citation chips are attached below the assistant message and expand on click.
- **Session continuity**: A UUID is generated client-side on first send and included in subsequent requests so the backend maintains conversation history.
- **Auto-scroll**: `MessageList` scrolls to the bottom on new tokens but stops if the user has scrolled up.
- **Responsive layout**: Sidebar slides in/out on mobile. Chat area fills available width on all screen sizes.

## Hooks

| Hook | Purpose |
|------|---------|
| `useChat` | Chat state, SSE streaming, session management |
| `useSearch` | Direct semantic search against `/api/search` |

## API Client

`src/api/client.ts` — thin fetch wrapper that handles SSE streaming and JSON requests. `src/api/types.ts` contains all TypeScript interfaces matching the backend schemas (`ChatEvent`, `SearchResult`, `TopicResponse`, `PageInfo`, `SourceRef`).

## Tech Stack

- React 18 with functional components and hooks only
- TypeScript (strict mode)
- Vite 5 (dev server + bundler)
- Tailwind CSS 3
