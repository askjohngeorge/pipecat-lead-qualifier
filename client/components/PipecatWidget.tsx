"use client";

import {
  useRTVIClient,
  useRTVIClientTransportState,
  useRTVIClientEvent,
  RTVIClientAudio,
} from "@pipecat-ai/client-react";
import { LLMFunctionCallData, RTVIEvent, LLMHelper } from "@pipecat-ai/client-js";
import { useCallback, useState, useEffect } from "react";
import { AIVoiceInput } from "./ui/ai-voice-input";

interface NavigationArgs {
  path: string;
}

export function PipecatWidget() {
  const client = useRTVIClient();
  const transportState = useRTVIClientTransportState();
  const isConnected = ["connected", "ready"].includes(transportState);
  const [isConnecting, setIsConnecting] = useState(false);

  // Initialize LLM helper
  useEffect(() => {
    if (client && !client.getHelper("llm")) {
      client.registerHelper("llm", new LLMHelper({}));
    }
  }, [client]);

  // Handle navigation function calls
  useRTVIClientEvent(
    RTVIEvent.LLMFunctionCall,
    useCallback((data: LLMFunctionCallData) => {
      if (data.function_name === "navigate" && typeof data.args === "object" && data.args && "path" in data.args) {
        const args = data.args as NavigationArgs;
        const { path } = args;

        // Replace the console.log with a navigation request in production
        console.log(`Navigation request received:`, { path });
      }
    }, [])
  );

  // Add handler for bot disconnect event
  useRTVIClientEvent(
    RTVIEvent.BotDisconnected,
    useCallback(async () => {
      // Reset all state
      setIsConnecting(false);

      if (client) {
        try {
          // Ensure client is fully disconnected
          if (isConnected) {
            await client.disconnect();
          }
        } catch (error) {
          console.error("Error during cleanup:", error);
        }
      }
    }, [client, isConnected])
  );

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
        console.error(isActive ? "Connection error:" : "Disconnection error:", error);
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
