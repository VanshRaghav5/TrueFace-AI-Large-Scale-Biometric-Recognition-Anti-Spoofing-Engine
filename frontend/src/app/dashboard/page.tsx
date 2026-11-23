 "use client";

import { useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function DashboardPage() {
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  useEffect(() => {
    fetch(`${apiBase}/health`).then((response) => response.json()).then(setHealth).catch(() => setHealth(null));
  }, []);
  const faceStatus = health?.models?.face_model?.status ?? "unavailable";
  const databaseStatus = health?.models?.database?.status ?? "unavailable";
  const voiceStatus = health?.models?.voice?.status;
  const voiceReady = voiceStatus === "ready";
  const antispoofStatus = health?.models?.voice?.antispoof;
  const antispoofReady = antispoofStatus === "ready";
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">System Dashboard</h1>
        <p className="text-sm text-tf-text-muted">Real-time status of pipeline branches, vector store, and risk engine.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Face Pipeline Status</h2>
          <div className="mt-2 text-2xl font-bold text-tf-warning">{faceStatus}</div>
          <p className="mt-1 text-xs text-tf-text-muted">ArcFace/SCRFD runtime and provider status</p>
        </div>
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Voice Pipeline Status</h2>
          <div className={`mt-2 text-2xl font-bold ${voiceReady ? "text-emerald-600" : "text-tf-warning"}`}>
            {voiceReady ? "Ready" : "Unavailable"}
          </div>
          <p className="mt-1 text-xs text-tf-text-muted">
            {voiceReady
              ? `${health?.models?.voice?.model_name ?? "Speaker verification"} · ${health?.models?.voice?.embedding_dimension ?? "—"}-d embeddings`
              : "Speaker verification model not loaded"}
          </p>
          <p className="mt-1 text-xs text-tf-text-muted">
            <span className={antispoofReady ? "text-emerald-600" : "text-tf-warning"}>
              {antispoofReady ? "Anti-Spoof: AASIST" : "Anti-Spoof: Fallback"}
            </span>
            {" — "}
            {health?.models?.voice?.antispoof_model_name ?? "acoustic_spectral_fallback"}
          </p>
        </div>
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Vector Store (FAISS)</h2>
          <div className="mt-2 text-2xl font-bold text-tf-text">{databaseStatus}</div>
          <p className="mt-1 text-xs text-tf-text-muted">Enrolled identities: {health?.models?.database?.enrolled_identity_count ?? "—"}</p>
        </div>
      </div>
    </div>
  );
}
