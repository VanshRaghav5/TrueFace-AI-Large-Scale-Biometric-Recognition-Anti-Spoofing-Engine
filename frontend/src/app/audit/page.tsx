"use client";

import { useEffect, useState } from "react";

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Audit Log &amp; Forensics</h1>
        <p className="text-sm text-tf-text-muted">
          Tamper-evident record of verification attempts, decisions, calibrated scores, and reason codes.
        </p>
      </div>

      <div className="border border-tf-border rounded-card bg-tf-surface overflow-hidden">
        <table className="min-w-full divide-y divide-tf-border text-sm">
          <thead className="bg-tf-surface-muted text-tf-text-muted text-left text-xs uppercase font-medium">
            <tr>
              <th className="px-6 py-3">Timestamp</th>
              <th className="px-6 py-3">Session ID</th>
              <th className="px-6 py-3">Claimed Subject</th>
              <th className="px-6 py-3">Decision</th>
              <th className="px-6 py-3">Face / PAD</th>
              <th className="px-6 py-3">Reason Codes</th>
              <th className="px-6 py-3">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-tf-border text-tf-text">
            {events.length === 0 ? (
              <tr><td colSpan={7} className="px-6 py-8 text-center text-tf-text-muted">
                {error || "No recent audit events recorded."}
              </td></tr>
            ) : events.map((event) => (
              <tr key={event.session_id}>
                <td className="px-6 py-3">{new Date(event.timestamp).toLocaleString()}</td>
                <td className="px-6 py-3 font-mono text-xs">{event.session_id}</td>
                <td className="px-6 py-3">{event.claimed_subject_id ?? "—"}</td>
                <td className="px-6 py-3">{event.overall_decision}</td>
                <td className="px-6 py-3 text-xs">
                  <div>Match: {event.face_similarity == null ? "—" : event.face_similarity.toFixed(3)}</div>
                  <div>Real: {event.face_liveness == null ? "—" : event.face_liveness.toFixed(3)}</div>
                  <div>Spoof: {event.face_pad_spoof == null ? "—" : event.face_pad_spoof.toFixed(3)}</div>
                </td>
                <td className="px-6 py-3">{event.reason_codes.join(", ")}</td>
                <td className="px-6 py-3">{event.latency_ms} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
