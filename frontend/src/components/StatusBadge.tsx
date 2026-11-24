"use client";

import { CheckCircle2, XCircle, Loader2, Shield } from "lucide-react";

interface StatusBadgeProps {
  status: "verified" | "scanning" | "denied" | "idle";
  label?: string;
  className?: string;
}

export default function StatusBadge({ status, label, className = "" }: StatusBadgeProps) {
  const configs = {
    verified: {
      icon: CheckCircle2,
      text: label || "VERIFIED",
      className: "badge-verified",
    },
    scanning: {
      icon: Loader2,
      text: label || "SCANNING",
      className: "badge-scanning",
    },
    denied: {
      icon: XCircle,
      text: label || "DENIED",
      className: "badge-denied",
    },
    idle: {
      icon: Shield,
      text: label || "IDLE",
      className: "badge",
    },
  };

  const config = configs[status];
  const Icon = config.icon;

  return (
    <div className={`${config.className} ${className}`}>
      <Icon className={`w-3.5 h-3.5 ${status === "scanning" ? "animate-spin" : ""}`} />
      {config.text}
    </div>
  );
}
