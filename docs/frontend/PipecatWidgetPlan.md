# Pipecat Audio Widget Implementation Plan

## Overview
Create a React component that provides an audio-only interface to the Pipecat voice assistant, replicating the core functionality of the existing VapiWidget but using Pipecat's RTVI client SDK.

## Server Component

### 1. Daily.co API Integration
```typescript
// server/daily.ts
import axios from 'axios';

const DAILY_API_KEY = process.env.DAILY_API_KEY;
const DAILY_API_URL = 'https://api.daily.co/v1';

interface RoomConfig {
  privacy: 'private';
  properties: {
    enable_network_ui: boolean;
    enable_screenshare: boolean;
    enable_chat: boolean;
    start_video_off: boolean;
    start_audio_off: boolean;
  };
}

async function createRoom() {
  const config: RoomConfig = {
    privacy: 'private',
    properties: {
      enable_network_ui: false,
      enable_screenshare: false,
      enable_chat: false,
      start_video_off: true,
      start_audio_off: false,
    },
  };

  const response = await axios.post(`${DAILY_API_URL}/rooms`, config, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${DAILY_API_KEY}`,
    },
  });

  return response.data;
}

async function createMeetingToken(roomName: string) {
  const response = await axios.post(
    `${DAILY_API_URL}/meeting-tokens`,
    {
      properties: {
        room_name: roomName,
        is_owner: false,
      },
    },
    {
      headers: {
        Authorization: `Bearer ${DAILY_API_KEY}`,
      },
    }
  );

  return response.data.token;
}
```

### 2. API Endpoints
```typescript
// server/api/routes/daily.ts
import { Router } from 'express';
import { createRoom, createMeetingToken } from '../daily';

const router = Router();

router.post('/room', async (req, res) => {
  try {
    const room = await createRoom();
    const token = await createMeetingToken(room.name);
    
    res.json({
      roomUrl: room.url,
      token,
    });
  } catch (error) {
    console.error('Failed to create room:', error);
    res.status(500).json({ error: 'Failed to create room' });
  }
});

export default router;
```

## Environment Variables

### Server
```env
DAILY_API_KEY=your_daily_api_key
```

### Client
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:3000/api
```

## Client Implementation

### 1. Room Connection Service
```typescript
// frontend/services/daily.ts
async function getDailyRoom() {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/daily/room`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error('Failed to get Daily room');
  }
  
  return response.json();
}
```

### 2. RTVI Client Setup
```typescript
import { RTVIClientAudio } from '@pipecat/client';
import { DailyTransport } from '@pipecat/daily-transport';

const { roomUrl, token } = await getDailyRoom();

const client = new RTVIClientAudio({
  transport: new DailyTransport(),
  params: {
    roomUrl,
    token,
    enableMic: true,
    enableCam: false,
    enableScreenShare: false,
    timeout: 15000,
  }
});
```

## Dependencies Required
```bash
npm install @pipecat/client @pipecat/daily-transport
```

## Component Structure

### 1. Core Component: `PipecatWidget.tsx`
- Use React hooks for state management (useState, useEffect, useRef)
- Maintain same UI/UX as current widget but simplified for audio-only
- Keep existing button states: idle, connecting, active

### 2. RTVI Client Setup
```typescript
import { RTVIClientAudio } from '@pipecat/client';
import { DailyTransport } from '@pipecat/daily-transport';

const client = new RTVIClientAudio({
  transport: new DailyTransport(),
  params: {
    roomUrl: process.env.NEXT_PUBLIC_PIPECAT_ROOM_URL,
    enableMic: true,
    enableCam: false,
    enableScreenShare: false,
    timeout: 15000,
  }
});
```

### 3. State Management
```typescript
interface State {
  callStatus: 'idle' | 'connecting' | 'active';
  isToggling: boolean;
}
```

### 4. Event Handlers
- Connected: Update status to active
- Disconnected: Reset status to idle
- Error: Handle connection failures
- Bot Ready: Enable interaction

### 5. Connection Management
- Implement debounced connect/disconnect
- Handle cleanup on component unmount
- Manage microphone permissions

## UI Components
- Maintain existing button design
- Keep status indicators and animations
- Preserve accessibility features

## Environment Setup
Required environment variables:
```
NEXT_PUBLIC_PIPECAT_ROOM_URL=your_daily_room_url
```

## Implementation Steps

1. Set up server environment with Daily API key
2. Implement server-side Daily.co integration
3. Create API endpoints for room/token generation
4. Create basic component structure
5. Implement RTVI client initialization with token auth
6. Add state management
7. Set up event handlers
8. Add connection management
9. Port over UI components
10. Add error handling
11. Test audio connectivity
12. Add loading states
13. Implement cleanup

## Key Differences from VapiWidget

1. **Transport Layer**
   - Replace Vapi's WebSocket with Daily's WebRTC transport
   - Focus on audio-only configuration

2. **Event System**
   - Use RTVI event system instead of Vapi events
   - Simplified event handling for audio-only use case

3. **Connection Flow**
   - Direct WebRTC connection to bot
   - No separate assistant ID needed

## Next Steps

1. Create initial implementation of `PipecatWidget.tsx`
2. Set up environment configuration
3. Test with existing bot implementation
4. Add error handling and recovery
5. Document usage instructions 

## Security Considerations

1. **API Key Protection**
   - Daily API key stays secure on the server
   - Never exposed to client-side code
   - Used only for room creation and token generation

2. **Room Access**
   - Rooms created with private privacy setting
   - Each connection requires a valid meeting token
   - Tokens are short-lived and room-specific

3. **Feature Restrictions**
   - Video disabled by default
   - Screen sharing disabled
   - Chat disabled
   - Network UI disabled

## Implementation Steps (Updated)

1. Set up server environment with Daily API key
2. Implement server-side Daily.co integration
3. Create API endpoints for room/token generation
4. Create basic component structure
5. Implement RTVI client initialization with token auth
6. Add state management
7. Set up event handlers
8. Add connection management
9. Port over UI components
10. Add error handling
11. Test audio connectivity
12. Add loading states
13. Implement cleanup 