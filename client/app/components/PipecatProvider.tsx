"use client";

import { RTVIClientProvider, RTVIClientAudio } from "@pipecat-ai/client-react";
import { createRTVIClient } from "../lib/rtviClient";

const client = createRTVIClient();

export function PipecatProvider({ children }: { children: React.ReactNode }) {
  return (
    <RTVIClientProvider client={client}>
      {children}
      <RTVIClientAudio />
    </RTVIClientProvider>
  );
}
