"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, ShieldCheck } from "lucide-react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function AuthenticationPage() {
  const [claimedId, setClaimedId] = useState("");
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [padResult, setPadResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [liveFaces, setLiveFaces] = useState<unknown[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const liveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (liveTimerRef.current) clearInterval(liveTimerRef.current);
  }, []);

  async function startCamera() {
    streamRef.current = await navigator.mediaDevices.getUserMedia({ video: true });
    if (videoRef.current) videoRef.current.srcObject = streamRef.current;
    liveTimerRef.current = setInterval(async () => {
      const video = videoRef.current;
      if (!video || video.videoWidth === 0) return;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth; canvas.height = video.videoHeight;
      canvas.getContext("2d")?.drawImage(video, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg"));
      if (!blob) return;
      const form = new FormData(); form.append("frame", blob, "live-frame.jpg");
      const response = await fetch(`${apiBase}/face/live`, { method: "POST", body: form });
      if (response.ok) setLiveFaces((await response.json()).faces ?? []);
    }, 750);
  }

  function captureFrame() {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) setFaceImage(new File([blob], "webcam-capture.jpg", { type: "image/jpeg" }));
    }, "image/jpeg");
  }

  async function verifyFace() {
    if (!faceImage) return;
    setSubmitting(true); setError(""); setResult(null); setPadResult(null);
    const form = new FormData();
    form.append("face_image", faceImage);
    if (claimedId) form.append("claimed_subject_id", claimedId);
    try {
      const response = await fetch(`${apiBase}/face/verify`, { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Face verification failed");
      setResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Face verification failed");
    } finally { setSubmitting(false); }
  }

  async function checkLiveness() {
    if (!faceImage) return;
    setSubmitting(true); setError(""); setPadResult(null);
    const form = new FormData();
    form.append("face_image", faceImage);
    try {
      const response = await fetch(`${apiBase}/face/pad`, { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Face liveness check failed");
      setPadResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Face liveness check failed");
    } finally { setSubmitting(false); }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div><h1 className="text-2xl font-bold text-tf-text">Face Verification</h1><p className="text-sm text-tf-text-muted">Upload a consented image for real ArcFace/SCRFD gallery matching.</p></div>
      <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-4">
        <h2 className="text-base font-semibold text-tf-text flex items-center gap-2"><Camera className="w-5 h-5 text-tf-primary" /> Face input</h2>
        <video ref={videoRef} autoPlay muted className="w-full rounded-input bg-black" />
        {liveFaces.length > 0 && (
          <div className="space-y-2">
            {liveFaces.map((face, index) => {
              const item = face as Record<string, unknown>;
              return (
                <div key={index} className="rounded-input border border-tf-border bg-tf-surface-muted p-3 text-xs text-tf-text">
                  <div className="font-semibold">Track {String(item.track_id ?? "—")}</div>
                  <div>Identity: {String(item.identity ?? "Unknown")} ({String(item.identity_state ?? "unknown")})</div>
                  <div>Similarity: {item.similarity == null ? "—" : String(item.similarity)}</div>
                  <div className="mt-1 font-semibold">PAD: {String(item.pad_state ?? "unavailable")}</div>
                  <div>Real: {item.pad_real_score == null ? "—" : String(item.pad_real_score)}</div>
                  <div>Spoof: {item.pad_spoof_score == null ? "—" : String(item.pad_spoof_score)}</div>
                  <div>Provider: {String(item.pad_provider ?? "unavailable")}</div>
                </div>
              );
            })}
          </div>
        )}
        <div className="flex gap-2">
          <button type="button" onClick={startCamera} className="rounded-input border border-tf-border px-3 py-2 text-sm">Start camera</button>
          <button type="button" onClick={captureFrame} className="rounded-input border border-tf-border px-3 py-2 text-sm">Capture frame</button>
        </div>
        <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFaceImage(e.target.files?.[0] ?? null)} className="block w-full text-xs text-tf-text-muted" />
        <div><label className="block text-sm font-medium text-tf-text">Claimed subject ID (optional 1:1 check)</label><input value={claimedId} onChange={(e) => setClaimedId(e.target.value)} className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm" /></div>
        <button onClick={verifyFace} disabled={!faceImage || submitting} className="w-full py-2.5 px-4 bg-tf-primary disabled:bg-tf-surface-muted text-white rounded-input text-sm font-medium flex items-center justify-center gap-2"><ShieldCheck className="w-4 h-4" />{submitting ? "Processing..." : "Verify face"}</button>
        <button onClick={checkLiveness} disabled={!faceImage || submitting} className="w-full py-2.5 px-4 border border-tf-primary text-tf-primary disabled:border-tf-border disabled:text-tf-text-muted rounded-input text-sm font-medium">Check face liveness</button>
        {error && <p className="text-sm text-tf-danger" role="alert">{error}</p>}
        {result && <pre className="overflow-auto rounded-input bg-tf-surface-muted p-3 text-xs text-tf-text">{JSON.stringify(result, null, 2)}</pre>}
        {padResult && <pre className="overflow-auto rounded-input bg-tf-surface-muted p-3 text-xs text-tf-text">{JSON.stringify(padResult, null, 2)}</pre>}
      </div>
    </div>
  );
}
