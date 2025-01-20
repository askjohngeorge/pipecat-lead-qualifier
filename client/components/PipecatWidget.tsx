"use client";

import {
  useRTVIClient,
  useRTVIClientTransportState,
  RTVIClientAudio,
} from "@pipecat-ai/client-react";
import { useCallback, useState } from "react";
import { AIVoiceInput } from "./ui/ai-voice-input";

export function PipecatWidget() {
  const client = useRTVIClient();
  const transportState = useRTVIClientTransportState();
  const isConnected = ["connected", "ready"].includes(transportState);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleStateChange = useCallback(
    async (isActive: boolean) => {
      if (!client) {
        console.error("RTVI client is not initialized");
        return;
      }

      try {
        if (isActive && !isConnected && !isConnecting) {
          setIsConnecting(true);
          await client.connect();
        } else if (!isActive && isConnected) {
          await client.disconnect();
        }
      } catch (error) {
        console.error(
          isActive ? "Connection error:" : "Disconnection error:",
          error
        );
        setIsConnecting(false);
      }
    },
    [client, isConnected, isConnecting]
  );

  return (
    <div className="fixed bottom-8 right-8 flex flex-col items-end gap-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg">
        <AIVoiceInput
          isActive={isConnected || isConnecting}
          onChange={handleStateChange}
          className="w-auto"
          demoMode={false}
        />
      </div>
      <RTVIClientAudio />
    </div>
  );
}
