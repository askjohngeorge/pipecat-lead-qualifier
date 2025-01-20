# Minimal Pipecat Widget Implementation

## Overview
Create a basic React component that connects to a public Daily room where the bot is running, using Pipecat's React SDK.

## Dependencies (Already Installed)
- @pipecat-ai/client-js
- @pipecat-ai/client-react
- @pipecat-ai/daily-transport

## Implementation

### 1. Environment Setup
```env
NEXT_PUBLIC_DAILY_ROOM_URL=https://your-domain.daily.co/your-room
```

### 2. RTVI Client Setup
```typescript
// app/lib/rtviClient.ts
import { RTVIClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";

export const createRTVIClient = () => new RTVIClient({
  transport: new DailyTransport(),
  params: {
    roomUrl: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
  },
  enableMic: true,
  enableCam: false,
  enableScreenShare: false,
  callbacks: {
    onBotConnected: () => {
      console.log("[CALLBACK] Bot connected");
    },
    onBotDisconnected: () => {
      console.log("[CALLBACK] Bot disconnected");
    },
    onBotReady: () => {
      console.log("[CALLBACK] Bot ready to chat!");
    },
  },
});
```

### 3. Provider Component
```typescript
// app/components/PipecatProvider.tsx
"use client";

import { RTVIClientProvider, RTVIClientAudio } from "@pipecat-ai/client-react";
import { createRTVIClient } from "../lib/rtviClient";

const client = createRTVIClient();

export function PipecatProvider({ children }: { children: React.ReactNode }) {
  return (
    <RTVIClientProvider client={client}>
      {children}
      <RTVIClientAudio />
    </RTVIClientProvider>
  );
}
```

### 4. Widget Component
```typescript
// app/components/PipecatWidget.tsx
"use client";

import { useRTVIClient } from "@pipecat-ai/client-react";
import { useState, useCallback } from "react";

export function PipecatWidget() {
  const [isConnected, setIsConnected] = useState(false);
  const client = useRTVIClient();

  const toggleCall = useCallback(async () => {
    if (isConnected) {
      await client.disconnect();
      setIsConnected(false);
    } else {
      try {
        await client.connect();
        setIsConnected(true);
      } catch (error) {
        console.error("Failed to connect:", error);
      }
    }
  }, [client, isConnected]);

  return (
    <button 
      onClick={toggleCall}
      className="fixed bottom-8 right-8 p-4 rounded-full bg-blue-500 text-white"
    >
      {isConnected ? "End Call" : "Start Call"}
    </button>
  );
}
```

### 5. App Integration
```typescript
// app/layout.tsx
import { PipecatProvider } from "./components/PipecatProvider";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <PipecatProvider>
          {children}
        </PipecatProvider>
      </body>
    </html>
  );
}
```

```typescript
// app/page.tsx
import { PipecatWidget } from "./components/PipecatWidget";

export default function Home() {
  return (
    <main>
      <PipecatWidget />
    </main>
  );
}
```

## Testing Steps

1. Start the bot in a public Daily room:
   ```bash
   # Configure bot.py with the public room URL
   python bot.py
   ```

2. Copy `.env.example` to `.env` and set your Daily room URL

3. Start the Next.js dev server:
   ```bash
   cd client
   pnpm dev
   ```

4. Test basic functionality:
   - Click button to connect
   - Verify audio connection with bot
   - Click again to disconnect

## Key Differences from Previous Plan

1. **Provider Pattern**
   - Uses RTVIClientProvider for state management
   - RTVIClientAudio component handles audio setup

2. **React Hooks**
   - useRTVIClient for accessing client instance
   - Better state management and cleanup

3. **Next.js Integration**
   - Provider at layout level
   - Client-side components properly marked

## Next Steps After Proof of Concept

1. Add proper error handling
2. Improve connection state management
3. Add loading states
4. Enhance UI with status indicators
5. Add private room security 