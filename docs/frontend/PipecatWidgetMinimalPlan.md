# Minimal Pipecat Widget Implementation

## Overview
Create a basic React component that connects to a public Daily room where the bot is running, using Pipecat's RTVI client SDK.

## Dependencies
```bash
npm install @pipecat/client @pipecat/daily-transport
```

## Minimal Implementation

### 1. Environment Setup
```env
NEXT_PUBLIC_DAILY_ROOM_URL=https://your-domain.daily.co/your-room
```

### 2. Basic Widget Component
```typescript
// frontend/components/PipecatWidget.tsx
import { useState, useCallback } from 'react';
import { RTVIClientAudio } from '@pipecat/client';
import { DailyTransport } from '@pipecat/daily-transport';

const PipecatWidget = () => {
  const [isConnected, setIsConnected] = useState(false);
  
  const toggleCall = useCallback(async () => {
    if (isConnected) {
      // Disconnect logic
      setIsConnected(false);
      return;
    }

    try {
      const client = new RTVIClientAudio({
        transport: new DailyTransport(),
        params: {
          roomUrl: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
          enableMic: true,
          enableCam: false,
          enableScreenShare: false,
        }
      });

      await client.connect();
      setIsConnected(true);
    } catch (error) {
      console.error('Failed to connect:', error);
    }
  }, [isConnected]);

  return (
    <button 
      onClick={toggleCall}
      className="fixed bottom-8 right-8 p-4 rounded-full bg-blue-500 text-white"
    >
      {isConnected ? 'End Call' : 'Start Call'}
    </button>
  );
};

export default PipecatWidget;
```

## Testing Steps

1. Start the bot in a public Daily room:
   ```bash
   # Configure bot.py with the public room URL
   python bot.py
   ```

2. Add widget to your app:
   ```typescript
   import PipecatWidget from './components/PipecatWidget';
   
   // In your app
   return (
     <div>
       <PipecatWidget />
     </div>
   );
   ```

3. Test basic functionality:
   - Click button to connect
   - Verify audio connection
   - Click again to disconnect

## Next Steps After Proof of Concept

1. Add proper error handling
2. Improve connection state management
3. Add loading states
4. Enhance UI with status indicators
5. Add private room security 