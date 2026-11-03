"use client";

import { useState } from "react";
import { ShieldCheck, Camera, Mic } from "lucide-react";

export default function AuthenticationPage() {
  const [claimedId, setClaimedId] = useState("");

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Biometric Authentication Verification</h1>
        <p className="text-sm text-tf-text-muted">
          Multimodal test harness evaluating identity similarity alongside presentation-attack and deepfake risk.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-4">
          <h2 className="text-base font-semibold text-tf-text flex items-center gap-2">
            <Camera className="w-5 h-5 text-tf-primary" />
            Face Verification &amp; PAD
          </h2>
          <div className="aspect-video bg-tf-surface-muted rounded-input border border-dashed border-tf-border flex flex-col items-center justify-center text-tf-text-muted p-4 text-center">
            <Camera className="w-8 h-8 mb-2 opacity-50" />
            <span className="text-xs">Webcam capture or test image upload</span>
          </div>
          <input
            type="file"
            accept="image/*"
            className="block w-full text-xs text-tf-text-muted file:mr-2 file:py-1.5 file:px-3 file:rounded-input file:border file:border-tf-border file:text-xs file:bg-tf-surface-muted"
          />
        </div>

        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-4">
          <h2 className="text-base font-semibold text-tf-text flex items-center gap-2">
            <Mic className="w-5 h-5 text-tf-primary" />
            Voice Verification &amp; Anti-Spoof
          </h2>
          <div className="aspect-video bg-tf-surface-muted rounded-input border border-dashed border-tf-border flex flex-col items-center justify-center text-tf-text-muted p-4 text-center">
            <Mic className="w-8 h-8 mb-2 opacity-50" />
            <span className="text-xs">Microphone recording or 16kHz WAV upload</span>
          </div>
          <input
            type="file"
            accept="audio/*"
            className="block w-full text-xs text-tf-text-muted file:mr-2 file:py-1.5 file:px-3 file:rounded-input file:border file:border-tf-border file:text-xs file:bg-tf-surface-muted"
          />
        </div>
      </div>

      <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-tf-text">Claimed Subject ID (1:1 Verification)</label>
          <input
            type="text"
            value={claimedId}
            onChange={(e) => setClaimedId(e.target.value)}
            placeholder="e.g. subj_1001 (leave blank for 1:N gallery search)"
            className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-tf-primary"
          />
        </div>

        <button
          className="w-full py-2.5 px-4 bg-tf-primary hover:bg-tf-primary-hover text-white rounded-input text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          <ShieldCheck className="w-4 h-4" />
          Execute Multimodal Verification
        </button>
      </div>
    </div>
  );
}

