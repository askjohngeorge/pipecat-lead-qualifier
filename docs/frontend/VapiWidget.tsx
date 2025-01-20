"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useButtonContext } from "~/contexts/ButtonContext";
import { log } from "~/utils/logging";
import Vapi from "@vapi-ai/web";

// Configurable delay for debounce and tooltip update (in milliseconds)
const INTERACTION_DELAY = 1000;

const debounce = (func: Function, delay: number) => {
  let timeoutId: NodeJS.Timeout;
  return (...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

const VapiWidget = () => {
  const pathname = usePathname();
  const {
    buttonText,
    buttonColor,
    isToggling,
    setButtonText,
    setButtonColor,
    setIsToggling,
  } = useButtonContext();
  const [callStatus, setCallStatus] = useState<
    "idle" | "connecting" | "active"
  >("idle");
  const vapiRef = useRef<Vapi | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (callStatus === "connecting") {
      setButtonText("Connecting Call...");
      setButtonColor("bg-connecting");
    } else if (callStatus === "active") {
      setButtonText("End AI Demo Call");
      setButtonColor("bg-accent");
    } else {
      setButtonText("Start AI Demo Call");
      setButtonColor("bg-accent");
    }
  }, [callStatus, setButtonText, setButtonColor]);

  useEffect(() => {
    if (!vapiRef.current) {
      vapiRef.current = new Vapi(
        process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY as string
      );
    }

    const vapi = vapiRef.current;

    vapi.on("call-start", () => {
      setCallStatus("active");
      setIsToggling(false);
    });
    vapi.on("call-end", () => {
      setCallStatus("idle");
      setIsToggling(false);
    });
    vapi.on("message", (message: any) => {
      log("Received message:", message);
      if (
        message.type === "tool-calls" &&
        message.toolCallList[0].function.name === "navigate-askjg"
      ) {
        const command =
          message.toolCallList[0].function.arguments.url.toLowerCase();
        if (command) {
          router.push(command);
        } else {
          console.error("Unknown route:", command);
        }
      }
    });

    return () => {
      vapi.removeAllListeners();
    };
  }, [router, setIsToggling]);

  const debouncedToggleCall = useCallback(() => {
    if (isToggling) return;
    setIsToggling(true);

    if (callStatus === "active" || callStatus === "connecting") {
      vapiRef.current?.stop();
      setCallStatus("idle");
    } else {
      setCallStatus("connecting");
      vapiRef.current?.start(
        process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID as string
      );
    }

    setTimeout(() => setIsToggling(false), INTERACTION_DELAY);
  }, [callStatus, isToggling, setIsToggling, vapiRef]);

  // Use debounce outside of useCallback
  const debouncedHandler = debounce(debouncedToggleCall, INTERACTION_DELAY);

  if (typeof window !== "undefined") {
    window.vapiWidget = {
      toggleCall: debouncedHandler,
    };
  }

  if (pathname === "/" && callStatus === "idle") {
    return null;
  }

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <div className="group relative">
        {pathname !== "/" ? (
          <button
            onClick={debouncedHandler}
            disabled={isToggling}
            className={`absolute bottom-full right-0 transform -translate-y-1 transition-opacity duration-300 mb-1
            ${
              callStatus === "idle"
                ? "opacity-0 group-hover:opacity-100"
                : "opacity-100"
            }
            text-white text-sm font-medium rounded-full py-2 px-4 whitespace-nowrap shadow-lg
            ${
              callStatus === "idle"
                ? "bg-accent"
                : callStatus === "connecting"
                ? "bg-connecting"
                : "bg-accent"
            }
            ${isToggling ? "cursor-not-allowed" : ""}`}
          >
            {buttonText}
          </button>
        ) : (
          ""
        )}
        <button
          onClick={debouncedHandler}
          disabled={isToggling}
          className={`w-16 h-16 rounded-full transition-all duration-300 ease-in-out focus:outline-none
            ${buttonColor}
            ${
              callStatus === "idle"
                ? "animate-pulse group-hover:animate-none"
                : ""
            }
            ${
              callStatus === "connecting"
                ? "animate-spin group-hover:animate-none"
                : ""
            }
            ${isToggling ? "cursor-not-allowed" : ""}`}
          aria-label={
            callStatus === "active"
              ? "End Call"
              : callStatus === "connecting"
              ? "Cancel Connection"
              : "Start Call"
          }
        >
          <span className="sr-only">
            {callStatus === "active"
              ? "End Call"
              : callStatus === "connecting"
              ? "Cancel Connection"
              : "Start Call"}
          </span>
          <div className="w-full h-full flex items-center justify-center">
            {callStatus === "active" ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-8 w-8 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            ) : callStatus === "connecting" ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-8 w-8 text-white animate-spin"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20 4v5h-.582m-15.356 2A8.001 8.001 0 0119.418 9m0 0H15M4 20v-5h.581m0 0a8.003 8.003 0 0015.357-2m-15.357 2H9"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 100 100"
                className="h-8 w-8 text-white"
              >
                <rect
                  className="stroke-current fill-none"
                  x="10"
                  y="20"
                  width="80"
                  height="70"
                  rx="10"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle className="fill-current" cx="50" cy="5" r="6" />
                <line
                  x1="50"
                  y1="11"
                  x2="50"
                  y2="20"
                  className="stroke-current"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle className="fill-current" cx="35" cy="45" r="6" />
                <circle className="fill-current" cx="65" cy="45" r="6" />
                <path
                  d="M30 70 Q50 80 70 70"
                  className="stroke-current fill-none"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <rect
                  className="stroke-current fill-none"
                  x="0"
                  y="40"
                  width="10"
                  height="30"
                  rx="5"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <rect
                  className="stroke-current fill-none"
                  x="90"
                  y="40"
                  width="10"
                  height="30"
                  rx="5"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
        </button>
      </div>
    </div>
  );
};

export default VapiWidget;
