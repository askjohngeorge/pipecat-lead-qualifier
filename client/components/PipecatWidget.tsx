"use client";

import {
  useRTVIClient,
  useRTVIClientTransportState,
  RTVIClientAudio,
} from "@pipecat-ai/client-react";
import { useCallback, useState, useEffect } from "react";
import { AIVoiceInput } from "./ui/ai-voice-input";

interface NavigationEventData {
  path: string;
  query?: Record<string, string>;
  replace?: boolean;
}

export function PipecatWidget() {
  const client = useRTVIClient();
  const transportState = useRTVIClientTransportState();
  const isConnected = ["connected", "ready"].includes(transportState);
  const [isConnecting, setIsConnecting] = useState(false);

  // Handle navigation events from the server
  useEffect(() => {
    if (!client) return;

    const handleMessage = (message: { type: string; data: unknown }) => {
      // Debug log for all messages
      console.log("RTVI message received:", message);

      if (message.type === "navigation-request") {
        const data = message.data as NavigationEventData;
        const queryString = data.query
          ? "?" + new URLSearchParams(data.query).toString()
          : "";

        console.log(`Navigation request received:`, {
          path: data.path + queryString,
          replace: data.replace,
        });
      }
    };

    // @ts-expect-error - RTVI client types don't include custom message events
    client.on("message", handleMessage);
    return () => {
      // @ts-expect-error - RTVI client types don't include custom message events
      client.off("message", handleMessage);
    };
  }, [client]);

  // Reset connecting state when transport state changes
  useEffect(() => {
    if (isConnected || transportState === "disconnected") {
      setIsConnecting(false);
    }
  }, [transportState, isConnected]);

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
