"use client";

import { useRTVIClient } from "@pipecat-ai/client-react";
import { useState, useCallback } from "react";

export function PipecatWidget() {
  const [isConnected, setIsConnected] = useState(false);
  const client = useRTVIClient();

  const toggleCall = useCallback(async () => {
    if (!client) return;

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
