"use client";

import { useEffect, useState, useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type AuditEvent = {
  timestamp: string;
  session_id: string;
  claimed_subject_id?: string | null;
  overall_decision: string;
  reason_codes: string[];
  face_similarity?: number | null;
  face_liveness?: number | null;
  face_pad_spoof?: number | null;
  voice_antispoof?: number | null;
  latency_ms: number;
};

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${apiBase}/audit/events?limit=50`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "Audit log unavailable");
        setEvents(payload.items ?? []);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Audit log unavailable"));
  }, []);

  const stats = useMemo(() => {
    const total = events.length;
    const allowed = events.filter(e => e.overall_decision === "allow").length;
    const blocked = total - allowed;
    const avgLatency = total > 0 
      ? Math.round(events.reduce((sum, e) => sum + e.latency_ms, 0) / total)
      : 0;
    
    return { total, allowed, blocked, avgLatency };
  }, [events]);

  const pieData = [
    { name: "Allow", value: stats.allowed, color: "#10b981" },
    { name: "Block", value: stats.blocked, color: "#f97316" },
  ];

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="panel p-6">
        <h1 className="text-2xl font-bold text-white">AUDIT LOG & FORENSICS</h1>
        <p className="text-xs text-gray-500 font-mono mt-1">
          Tamper-evident record of verification attempts, decisions, calibrated scores, and reason codes
        </p>
      </div>

      {/* Summary Strip with Donut Chart */}
      <div className="panel p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center">
          <div className="text-center">
            <div className="text-3xl font-mono font-bold text-white telemetry">
              {stats.total}
            </div>
            <div className="text-xs text-gray-600 font-mono uppercase tracking-wider mt-1">
              Total Attempts
            </div>
          </div>
          
          <div className="flex justify-center">
            <ResponsiveContainer width={100} height={100}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx={50}
                  cy={50}
                  innerRadius={30}
                  outerRadius={45}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-mono font-bold text-tf-accent telemetry">
              {stats.avgLatency}ms
            </div>
            <div className="text-xs text-gray-600 font-mono uppercase tracking-wider mt-1">
              Avg Latency
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-xl font-mono font-bold text-tf-accent telemetry">
                {stats.allowed}
              </div>
              <div className="text-xs text-gray-600 font-mono">Allowed</div>
            </div>
            <div>
              <div className="text-xl font-mono font-bold text-tf-alert telemetry">
                {stats.blocked}
              </div>
              <div className="text-xs text-gray-600 font-mono">Blocked</div>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Table */}
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-tf-border text-sm">
            <thead className="bg-tf-surface text-left">
              <tr>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Timestamp</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Session</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Subject</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Decision</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Scores</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Reason Codes</th>
                <th className="px-4 py-3 text-xs font-mono uppercase tracking-wider text-gray-500">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-tf-border">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <div className="text-gray-600 font-mono text-sm">
                      {error || "No recent audit events recorded"}
                    </div>
                  </td>
                </tr>
              ) : events.map((event) => (
                <tr key={event.session_id} className="hover:bg-tf-surface transition-colors">
                  <td className="px-4 py-3 text-xs text-gray-400 font-mono">
                    {new Date(event.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-500">
                    {event.session_id.substring(0, 12)}...
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-white">
                    {event.claimed_subject_id ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {event.overall_decision === "allow" ? (
                      <span className="badge-verified text-xs">ALLOW</span>
                    ) : (
                      <span className="badge-denied text-xs">BLOCK</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs space-y-1">
                    {/* Visual Score Bars */}
                    {event.face_liveness != null && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 font-mono w-12">Real:</span>
                        <div className="flex-1 h-1 bg-tf-border">
                          <div 
                            className="h-full bg-tf-accent"
                            style={{ width: `${event.face_liveness * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono telemetry text-tf-accent w-12">
                          {(event.face_liveness * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                    {event.face_pad_spoof != null && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 font-mono w-12">Spoof:</span>
                        <div className="flex-1 h-1 bg-tf-border">
                          <div 
                            className="h-full bg-tf-alert"
                            style={{ width: `${event.face_pad_spoof * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono telemetry text-tf-alert w-12">
                          {(event.face_pad_spoof * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {event.reason_codes.map((code, idx) => (
                        <span 
                          key={idx}
                          className="inline-block px-2 py-0.5 border border-tf-border text-xs font-mono text-gray-500"
                        >
                          {code}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono telemetry text-gray-400">
                    {event.latency_ms}ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-gray-600 font-mono">
        © {new Date().getFullYear()} TrueFace AI-X. All rights reserved.
      </div>
    </div>
  );
}
