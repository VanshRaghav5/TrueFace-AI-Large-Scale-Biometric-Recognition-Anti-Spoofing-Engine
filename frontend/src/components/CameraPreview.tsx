"use client";

import { RefObject } from "react";
import { Camera, StopCircle } from "lucide-react";

interface CameraPreviewProps {
  videoRef: RefObject<HTMLVideoElement>;
  isActive: boolean;
  isScanning?: boolean;
  onCapture?: () => void;
  onStop?: () => void;
  className?: string;
}

export default function CameraPreview({
  videoRef,
  isActive,
  isScanning = false,
  onCapture,
  onStop,
  className = "",
}: CameraPreviewProps) {
  return (
    <div className={`relative ${className}`}>
      {/* Camera feed */}
      <div className="relative aspect-video bg-tf-bg overflow-hidden viewfinder">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
        
        {/* Corner brackets */}
        {isActive && (
          <div className="brackets">
            <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-emerald-400" />
            <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-emerald-400" />
            <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-emerald-400" />
            <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-emerald-400" />
          </div>
        )}

        {/* Scan line animation */}
        {isScanning && (
          <div className="scan-line" />
        )}

        {/* Inactive state */}
        {!isActive && (
          <div className="absolute inset-0 flex items-center justify-center bg-tf-bg">
            <div className="text-center space-y-3">
              <Camera className="w-12 h-12 mx-auto text-gray-700" />
              <p className="text-xs text-gray-600 font-mono uppercase tracking-wider">Camera Inactive</p>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      {isActive && (
        <div className="mt-3 grid grid-cols-2 gap-2">
          {onCapture && (
            <button
              type="button"
              onClick={onCapture}
              className="btn-primary"
            >
              <Camera className="w-4 h-4" />
              Capture
            </button>
          )}
          {onStop && (
            <button
              type="button"
              onClick={onStop}
              className="btn-secondary"
            >
              <StopCircle className="w-4 h-4" />
              Stop
            </button>
          )}
        </div>
      )}
    </div>
  );
}
