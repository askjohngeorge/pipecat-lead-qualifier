"use client";

import {
  useRTVIClient,
  useRTVIClientTransportState,
  // RTVIClientVideo,
  RTVIClientAudio,
} from "@pipecat-ai/client-react";
import { useCallback } from "react";

export function PipecatWidget() {
  const client = useRTVIClient();
  const transportState = useRTVIClientTransportState();
  const isConnected = ["connected", "ready"].includes(transportState);

  const handleConnect = useCallback(async () => {
    if (!client) {
      console.error("RTVI client is not initialized");
      return;
    }

    try {
      if (isConnected) {
        await client.disconnect();
      } else {
        await client.connect();
      }
    } catch (error) {
      console.error("Connection error:", error);
    }
  }, [client, isConnected]);

  return (
    <div className="fixed bottom-8 right-8 flex flex-col items-end gap-4">
      {/* {isConnected && (
        <div className="w-80 h-48 bg-gray-200 rounded-lg overflow-hidden">
          <RTVIClientVideo participant="bot" fit="cover" />
        </div>
      )} */}
      <button
        onClick={handleConnect}
        disabled={
          !client || ["connecting", "disconnecting"].includes(transportState)
        }
        className={`p-4 rounded-full text-white ${
          isConnected ? "bg-red-500" : "bg-blue-500"
        } disabled:opacity-50`}
      >
        {isConnected ? "End Call" : "Start Call"}
      </button>
      <RTVIClientAudio />
    </div>
  );
}
