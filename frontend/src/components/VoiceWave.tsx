"use client";

import dynamic from "next/dynamic";

const Player = dynamic(
  () => import("@lottiefiles/react-lottie-player").then((mod) => mod.Player),
  { ssr: false }
);

interface VoiceWaveProps {
  isRecording: boolean;
  className?: string;
}

export default function VoiceWave({ isRecording, className = "" }: VoiceWaveProps) {
  return (
    <div className={`voice-wave-container ${className}`} style={{ pointerEvents: 'none' }}>
      <Player
        autoplay={isRecording}
        loop={isRecording}
        src="/voice-wave.json"
        style={{
          width: "100%",
          height: "100%",
          pointerEvents: 'none',
        }}
      />
    </div>
  );
}
