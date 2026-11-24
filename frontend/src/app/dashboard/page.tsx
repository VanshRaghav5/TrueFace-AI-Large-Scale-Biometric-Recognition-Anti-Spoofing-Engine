"use client";

import { useEffect, useState } from "react";
import { Activity, Shield, Database, Mic, Eye, Cpu, AlertCircle, CheckCircle, XCircle } from "lucide-react";
import LatencySparkline from "@/components/charts/LatencySparkline";
import CircularGauge from "@/components/charts/CircularGauge";
import VolumeChart from "@/components/charts/VolumeChart";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function DashboardPage() {
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiBase}/health`)
      .then((response) => response.json())
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch(() => {
        setHealth(null);
        setLoading(false);
      });
  }, []);

  const faceStatus = health?.models?.face_model?.status ?? "unavailable";
  const databaseStatus = health?.models?.database?.status ?? "unavailable";
  const voiceStatus = health?.models?.voice?.status ?? "unavailable";
  const antispoofStatus = health?.models?.voice?.antispoof ?? "unavailable";
  const enrolledCount = health?.models?.database?.enrolled_identity_count ?? 0;

  // Mock 24h volume data (in production, fetch from backend)
  const volumeData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i.toString().padStart(2, '0')}:00`,
    count: Math.floor(Math.random() * 100) + 20,
  }));

  // Mock system metrics
  const cpuUsage = Math.random() * 100;
  const memoryUsage = Math.random() * 100;

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-tf-surface border border-tf-border flex items-center justify-center">
              <Activity className="w-6 h-6 text-tf-accent" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">SYSTEM DASHBOARD</h1>
              <p className="text-xs text-gray-500 font-mono mt-1">REAL-TIME PIPELINE STATUS AND MODEL HEALTH</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatusCard
          icon={<Eye className="w-6 h-6" />}
          title="Face Pipeline"
          status={faceStatus}
          loading={loading}
          details={[
            { label: "Model", value: health?.models?.face_model?.model_name ?? "—" },
            { label: "Provider", value: health?.models?.face_model?.providers?.[0] ?? "—" },
          ]}
        />

        <StatusCard
          icon={<Mic className="w-6 h-6" />}
          title="Voice Pipeline"
          status={voiceStatus}
          loading={loading}
          details={[
            { label: "Model", value: health?.models?.voice?.model_name ?? "—" },
            { label: "Anti-Spoof", value: antispoofStatus === "ready" ? "Active" : "Fallback" },
            { label: "Dimension", value: `${health?.models?.voice?.embedding_dimension ?? "—"}D` },
          ]}
        />

        <StatusCard
          icon={<Database className="w-6 h-6" />}
          title="Vector Store"
          status={databaseStatus}
          loading={loading}
          details={[
            { label: "Type", value: "Vector DB" },
            { label: "Enrolled", value: `${enrolledCount} identities` },
          ]}
        />
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="panel p-6 flex flex-col items-center justify-center">
          <CircularGauge value={cpuUsage} label="CPU Usage" unit="%" />
        </div>
        <div className="panel p-6 flex flex-col items-center justify-center">
          <CircularGauge value={memoryUsage} label="Memory Usage" unit="%" />
        </div>
        <div className="lg:col-span-1">
          <VolumeChart data={volumeData} />
        </div>
      </div>

      {/* Detailed Models Status */}
      <div className="panel p-6">
        <h2 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-6 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-tf-accent" />
          Model Runtime Details
        </h2>
        <div className="space-y-3">
          <ModelRow
            name="Face Detector"
            model="Detection Model"
            status={health?.models?.face_detector}
            provider={health?.models?.face_model?.providers?.[0]}
          />
          <ModelRow
            name="Face Recognizer"
            model="Recognition Model"
            status={health?.models?.face_recognizer}
            provider={health?.models?.face_model?.providers?.[0]}
          />
          <ModelRow
            name="Face Liveness (PAD)"
            model={health?.models?.face_pad?.model_name ?? "Liveness Model"}
            status={health?.models?.face_pad?.status}
            provider={health?.models?.face_pad?.provider}
          />
          <ModelRow
            name="Deepfake Detection"
            model={typeof health?.models?.face_deepfake === 'object' 
              ? (health?.models?.face_deepfake?.model_name ?? "Deepfake Model")
              : "Deepfake Model"}
            status={typeof health?.models?.face_deepfake === 'object' 
              ? health?.models?.face_deepfake?.status 
              : health?.models?.face_deepfake}
            provider={typeof health?.models?.face_deepfake === 'object'
              ? health?.models?.face_deepfake?.provider
              : "ONNX"}
          />
          <ModelRow
            name="Voice Recognition"
            model={health?.models?.voice?.model_name ?? "Voice Model"}
            status={health?.models?.voice_recognizer}
            dimension={health?.models?.voice?.embedding_dimension}
          />
          <ModelRow
            name="Voice Anti-Spoof"
            model={health?.models?.voice?.antispoof_model_name ?? "Anti-Spoof Model"}
            status={health?.models?.voice_antispoof}
          />
        </div>
      </div>
    </div>
  );
}

function StatusCard({
  icon,
  title,
  status,
  loading,
  details,
}: {
  icon: React.ReactNode;
  title: string;
  status: string;
  loading: boolean;
  details: Array<{ label: string; value: string }>;
}) {
  const isReady = status === "ready";
  const statusColor = isReady ? "text-emerald-400" : "text-amber-400";
  const StatusIcon = isReady ? CheckCircle : AlertCircle;

  return (
    <div className="panel p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 bg-tf-surface border border-tf-border flex items-center justify-center">
          <div className="text-tf-accent">{icon}</div>
        </div>
        {loading ? (
          <span className="badge text-gray-500">LOADING...</span>
        ) : (
          <span className={isReady ? "badge-verified" : "badge-scanning"}>
            {status.toUpperCase()}
          </span>
        )}
      </div>
      <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">{title}</h3>
      
      {/* Latency Sparkline */}
      {isReady && (
        <div className="mb-4">
          <LatencySparkline />
        </div>
      )}
      
      <div className="space-y-2">
        {details.map((detail, idx) => (
          <div key={idx} className="flex justify-between text-xs">
            <span className="text-gray-600 font-mono">{detail.label}</span>
            <span className="text-gray-300 font-mono telemetry">{detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelRow({
  name,
  model,
  status,
  provider,
  dimension,
}: {
  name: string;
  model: string;
  status?: string;
  provider?: string;
  dimension?: number;
}) {
  const isReady = status === "ready" || status === "configured";
  const StatusIcon = isReady ? CheckCircle : status === "unavailable" ? XCircle : AlertCircle;
  const statusColor = isReady ? "text-emerald-400" : status === "unavailable" ? "text-orange-400" : "text-amber-400";

  return (
    <div className="flex items-center justify-between p-4 panel">
      <div className="flex items-center gap-3">
        <StatusIcon className={`w-4 h-4 ${statusColor}`} />
        <div>
          <div className="text-sm font-mono text-white">{name}</div>
          <div className="text-xs text-gray-600 font-mono">
            {model}
            {provider && ` · ${provider}`}
            {dimension && ` · ${dimension}D`}
          </div>
        </div>
      </div>
      <div className={`px-3 py-1 text-xs font-mono uppercase tracking-wider ${statusColor}`}>
        {status ?? "Unknown"}
      </div>
    </div>
  );
}
