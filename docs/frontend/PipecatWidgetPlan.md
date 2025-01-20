# Pipecat Audio Widget Implementation Plan

## Overview
Create a React component that provides an audio-only interface to the Pipecat voice assistant, replicating the core functionality of the existing VapiWidget but using Pipecat's RTVI client SDK.

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

1. Create basic component structure
2. Implement RTVI client initialization
3. Add state management
4. Set up event handlers
5. Add connection management
6. Port over UI components
7. Add error handling
8. Test audio connectivity
9. Add loading states
10. Implement cleanup

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