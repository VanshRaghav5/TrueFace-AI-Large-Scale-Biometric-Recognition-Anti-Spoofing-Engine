"use client";

import { useEffect, useRef } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Loader2, Shield } from "lucide-react";

export interface TerminalEvent {
  timestamp: Date;
  status: "success" | "error" | "warning" | "processing" | "info";
  message: string;
  detail?: string;
}

interface TerminalLogProps {
  events: TerminalEvent[];
  maxHeight?: string;
  className?: string;
}

const statusIcons = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  processing: Loader2,
  info: Shield,
};

const statusColors = {
  success: "text-emerald-400",
  error: "text-orange-400",
  warning: "text-yellow-400",
  processing: "text-gray-400",
  info: "text-gray-300",
};

export default function TerminalLog({ events, maxHeight = "24rem", className = "" }: TerminalLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const formatTimestamp = (date: Date): string => {
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    const seconds = date.getSeconds().toString().padStart(2, "0");
    const ms = date.getMilliseconds().toString().padStart(3, "0");
    return `${hours}:${minutes}:${seconds}.${ms}`;
  };

  return (
    <div className={`terminal ${className}`}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-tf-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-gray-400 font-mono uppercase tracking-wider">Event Log</span>
        </div>
        <span className="text-xs text-gray-600 font-mono">{events.length} events</span>
      </div>
      <div
        ref={scrollRef}
        className="overflow-y-auto px-4 py-3 space-y-1"
        style={{ maxHeight }}
      >
        {events.length === 0 ? (
          <div className="py-8 text-center">
            <Shield className="w-8 h-8 mx-auto mb-3 text-gray-700" />
            <p className="text-xs text-gray-600 font-mono">Waiting for verification events...</p>
          </div>
        ) : (
          events.map((event, index) => {
            const Icon = statusIcons[event.status];
            const colorClass = statusColors[event.status];
            return (
              <div key={index} className="terminal-line group">
                <span className="terminal-timestamp">{formatTimestamp(event.timestamp)}</span>
                <Icon
                  className={`w-3 h-3 ${colorClass} flex-shrink-0 ${
                    event.status === "processing" ? "animate-spin" : ""
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <span className={`text-xs font-mono ${colorClass}`}>{event.message}</span>
                  {event.detail && (
                    <span className="text-xs text-gray-600 ml-2 font-mono">— {event.detail}</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
