"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const Player = dynamic(
  () => import("@lottiefiles/react-lottie-player").then((mod) => mod.Player),
  { ssr: false }
);

export interface VerificationStage {
  stage: "face" | "voice" | "pin" | "complete";
  status: "pending" | "processing" | "success" | "failed";
  timestamp?: Date;
}

interface VerificationStagesProps {
  stages: VerificationStage[];
  className?: string;
}

const stageConfig = {
  face: {
    label: "Face Recognition",
    animation: "/face-id.json",
    color: "text-emerald-400",
    description: "Biometric face match",
  },
  voice: {
    label: "Voice Biometric",
    animation: "/voice-wave.json",
    color: "text-emerald-400",
    description: "Voice pattern analysis",
  },
  pin: {
    label: "PIN Validation",
    animation: "/pin-validation.json",
    color: "text-emerald-400",
    description: "Security code verification",
  },
  complete: {
    label: "Access Granted",
    animation: "/lock-verified.json",
    color: "text-emerald-400",
    description: "Authentication complete",
  },
};

export default function VerificationStages({ stages, className = "" }: VerificationStagesProps) {
  const [currentStage, setCurrentStage] = useState<VerificationStage | null>(null);
  const [showAnimation, setShowAnimation] = useState(false);

  useEffect(() => {
    const latestStage = stages.length > 0 ? stages[stages.length - 1] : null;
    if (latestStage && (latestStage.status === "processing" || latestStage.status === "success")) {
      setCurrentStage(latestStage);
      setShowAnimation(true);
    }
  }, [stages]);

  if (!currentStage || !showAnimation) {
    return null;
  }

  const config = stageConfig[currentStage.stage];

  return (
    <div className={`panel p-8 ${className}`}>
      <div className="flex flex-col items-center space-y-6">
        {/* Animation */}
        <div className="relative w-48 h-48">
          <Player
            autoplay
            loop={currentStage.status === "processing"}
            src={config.animation}
            style={{ width: "100%", height: "100%" }}
          />
        </div>

        {/* Stage info */}
        <div className="text-center space-y-2">
          <h3 className={`text-lg font-mono uppercase tracking-wider ${config.color}`}>
            {config.label}
          </h3>
          <p className="text-xs text-gray-500 font-mono">{config.description}</p>
          
          {currentStage.status === "processing" && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-mono text-gray-400">PROCESSING...</span>
            </div>
          )}
          
          {currentStage.status === "success" && (
            <div className="mt-4">
              <span className="badge-verified">VERIFIED</span>
            </div>
          )}
          
          {currentStage.status === "failed" && (
            <div className="mt-4">
              <span className="badge-denied">FAILED</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
