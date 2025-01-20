import { RTVIClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";

export const createRTVIClient = () => new RTVIClient({
  transport: new DailyTransport(),
  params: {
    roomUrl: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
  },
  enableMic: true,
  enableCam: false,
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