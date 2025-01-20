import { RTVIClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import type { TransportState } from "@pipecat-ai/client-js";

let client: RTVIClient | null = null;

export function getClient() {
  if (typeof window === 'undefined') return null;
  
  if (!client) {
    if (!process.env.NEXT_PUBLIC_DAILY_ROOM_URL) {
      console.error('Daily room URL not configured. Please set NEXT_PUBLIC_DAILY_ROOM_URL in .env.local');
      return null;
    }

    // Initialize Daily transport
    const transport = new DailyTransport();

    client = new RTVIClient({
      transport,
      params: {
        baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000",
        endpoints: {
          connect: "/connect",
        },
        // Pass the Daily room URL through the connect params
        dailyUrl: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
      },
      enableMic: true,
      enableCam: false,
    });

    // Add client event listeners for debugging
    client.on('error', (error) => {
      console.error('RTVI client error:', error);
    });

    client.on('transportStateChanged', (state: TransportState) => {
      console.log('Transport state changed:', state);
    });
  }
  
  return client;
} 