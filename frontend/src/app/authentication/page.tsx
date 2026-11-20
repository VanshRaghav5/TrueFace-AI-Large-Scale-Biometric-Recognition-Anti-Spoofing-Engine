"use client";

import { useEffect, useRef, useState } from "react";
import {
  Camera,
  ShieldCheck,
  Upload,
  UserCheck,
  UserX,
  Cpu,
  Clock,
  Scan,
  ShieldAlert,
  AlertCircle,
} from "lucide-react";

interface FaceResultData {
  status: string;
  face_detected: boolean;
  bounding_box: [number, number, number, number] | null;
  identity: string | null;
  recognition_state: "known" | "unknown";
  identity_similarity: number | null;
  model_name: string;
  providers: string[];
  processing_time_ms: number;
  liveness_score: number | null;
  pad_spoof_score: number | null;
  pad_state: string;
  pad_provider: string | null;
  reason_codes: string[];
}

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export default function AuthenticationPage() {
  const [claimedId, setClaimedId] = useState("");
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<FaceResultData | null>(null);
  const [padResult, setPadResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Camera handling
  const [useCamera, setUseCamera] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  async function startCamera() {
    try {
      setUseCamera(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
    } catch {
      setError("Webcam access denied or unavailable.");
      setUseCamera(false);
    }
  }

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  }

  function captureFrame() {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `auth_capture_${Date.now()}.jpg`, { type: "image/jpeg" });
        setFaceImage(file);
        setPreview(URL.createObjectURL(blob));
        stopCamera();
        setUseCamera(false);
      }
    }, "image/jpeg", 0.95);
  }

  async function verifyFace() {
    if (!faceImage) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    setPadResult(null);

    const form = new FormData();
    form.append("face_image", faceImage);
    if (claimedId.trim()) {
      form.append("claimed_subject_id", claimedId.trim());
    }

    try {
      const response = await fetch(`${apiBase}/face/verify`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Face verification failed");
      }
      setResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Face verification failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function checkLiveness() {
    if (!faceImage) return;
    setSubmitting(true);
    setError(null);
    setPadResult(null);

    const form = new FormData();
    form.append("face_image", faceImage);

    try {
      const response = await fetch(`${apiBase}/face/pad`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Face liveness check failed");
      }
      setPadResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Face liveness check failed");
    } finally {
      setSubmitting(false);
    }
  }

  const isMatched = result?.recognition_state === "known" && Boolean(result?.identity);
  const similarityScore = result?.identity_similarity !== null && result?.identity_similarity !== undefined
    ? Number(result.identity_similarity)
    : null;

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Face Recognition & Verification</h1>
        <p className="text-sm text-tf-text-muted mt-1">
          Perform 1:1 identity verification or 1:N open gallery recognition using InsightFace ArcFace embeddings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Input Card */}
        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6 shadow-sm">
          <h2 className="text-base font-semibold text-tf-text flex items-center gap-2">
            <Camera className="w-5 h-5 text-tf-primary" /> Face Input Source
          </h2>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (useCamera) stopCamera();
                setUseCamera(false);
              }}
              className={`flex-1 py-2 px-3 rounded-input text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                !useCamera
                  ? "bg-tf-primary text-white border-tf-primary"
                  : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
              }`}
            >
              <Upload className="w-3.5 h-3.5" /> Upload File
            </button>
            <button
              type="button"
              onClick={startCamera}
              className={`flex-1 py-2 px-3 rounded-input text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                useCamera
                  ? "bg-tf-primary text-white border-tf-primary"
                  : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
              }`}
            >
              <Camera className="w-3.5 h-3.5" /> Live Camera
            </button>
          </div>

          {useCamera ? (
            <div className="space-y-2">
              <div className="relative aspect-video rounded-input overflow-hidden bg-black border border-tf-border">
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
              </div>
              {cameraActive && (
                <button
                  type="button"
                  onClick={captureFrame}
                  className="w-full py-2 bg-tf-success text-white rounded-input text-xs font-medium flex items-center justify-center gap-1.5"
                >
                  <Camera className="w-3.5 h-3.5" /> Capture Frame
                </button>
              )}
            </div>
          ) : (
            <div>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null;
                  setFaceImage(file);
                  setPreview(file ? URL.createObjectURL(file) : null);
                }}
                className="block w-full text-xs text-tf-text-muted file:mr-3 file:py-1.5 file:px-3 file:rounded-input file:border-0 file:text-xs file:font-medium file:bg-tf-surface-muted file:text-tf-text hover:file:bg-tf-border"
              />
            </div>
          )}

          {preview && (
            <div className="rounded-input overflow-hidden border border-tf-border bg-tf-surface-muted p-1">
              <img src={preview} alt="Selected face preview" className="max-h-48 w-full rounded-input object-contain" />
            </div>
          )}

          <div className="space-y-1">
            <label className="block text-sm font-medium text-tf-text">
              Claimed Subject ID <span className="text-xs text-tf-text-muted">(Optional)</span>
            </label>
            <input
              value={claimedId}
              onChange={(e) => setClaimedId(e.target.value)}
              placeholder="Leave blank for 1:N gallery search, or enter ID for 1:1 match"
              className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:border-tf-primary"
            />
            <p className="text-[11px] text-tf-text-muted">
              Blank: searches entire enrolled gallery. Specified: verifies directly against claimed identity.
            </p>
          </div>

          <div className="space-y-2 pt-2">
            <button
              onClick={verifyFace}
              disabled={!faceImage || submitting}
              className="w-full py-2.5 px-4 bg-tf-primary disabled:bg-tf-surface-muted disabled:text-tf-text-muted text-white rounded-input text-sm font-medium flex items-center justify-center gap-2 transition-colors hover:bg-tf-primary-hover shadow-sm"
            >
              <ShieldCheck className="w-4 h-4" />
              {submitting ? "Processing Recognition..." : "Run Face Recognition"}
            </button>
            <button
              onClick={checkLiveness}
              disabled={!faceImage || submitting}
              className="w-full py-2 px-4 border border-tf-border text-tf-text disabled:border-tf-border disabled:text-tf-text-muted hover:bg-tf-surface-muted rounded-input text-xs font-medium transition-colors"
            >
              Check Face Liveness (PAD)
            </button>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-800 border border-red-200 rounded-input text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Results Card */}
        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-tf-text border-b border-tf-border pb-3">
              Recognition Forensics
            </h2>

            {!result && !padResult ? (
              <div className="py-20 text-center text-xs text-tf-text-muted">
                Capture or upload a face image and click "Run Face Recognition" to see live biometric matching results.
              </div>
            ) : (
              <div className="space-y-5 pt-4">
                {/* Decision Header */}
                {result && (
                  <div
                    className={`p-4 rounded-card border flex items-center justify-between ${
                      isMatched
                        ? "bg-emerald-50 border-emerald-200 text-emerald-950"
                        : "bg-rose-50 border-rose-200 text-rose-950"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {isMatched ? (
                        <div className="w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                          <UserCheck className="w-6 h-6" />
                        </div>
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-rose-500 text-white flex items-center justify-center">
                          <UserX className="w-6 h-6" />
                        </div>
                      )}
                      <div>
                        <div className="text-sm font-bold uppercase tracking-wider">
                          {isMatched ? "Identity Verified" : "Identity Unknown"}
                        </div>
                        <div className="text-xs font-semibold">
                          {isMatched ? `Subject: ${result.identity}` : "No match above threshold (0.75)"}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Similarity Meter */}
                {similarityScore !== null && (
                  <div className="space-y-2 p-3 bg-tf-surface-muted rounded-input border border-tf-border">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-tf-text">Cosine Similarity</span>
                      <span className="font-mono font-bold text-tf-primary">
                        {(similarityScore * 100).toFixed(2)}% ({(similarityScore).toFixed(4)})
                      </span>
                    </div>
                    <div className="w-full bg-tf-border h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          similarityScore >= 0.75 ? "bg-emerald-500" : "bg-amber-500"
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, similarityScore * 100))}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-tf-text-muted">
                      <span>0.00 (Dissimilar)</span>
                      <span className="font-semibold">Threshold: 0.75</span>
                      <span>1.00 (Identical)</span>
                    </div>
                  </div>
                )}

                {/* Technical Execution Metrics */}
                {result && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border space-y-1">
                      <div className="text-tf-text-muted flex items-center gap-1 text-[11px]">
                        <Clock className="w-3.5 h-3.5" /> Latency
                      </div>
                      <div className="font-semibold text-tf-text">{result.processing_time_ms} ms</div>
                    </div>
                    <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border space-y-1">
                      <div className="text-tf-text-muted flex items-center gap-1 text-[11px]">
                        <Cpu className="w-3.5 h-3.5" /> Hardware Provider
                      </div>
                      <div className="font-semibold text-tf-text truncate" title={result.providers.join(", ")}>
                        {result.providers[0] ?? "CPU"}
                      </div>
                    </div>
                  </div>
                )}

                {/* Detection Details */}
                {result?.bounding_box && (
                  <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border text-xs space-y-1">
                    <div className="text-tf-text-muted flex items-center gap-1 text-[11px]">
                      <Scan className="w-3.5 h-3.5" /> SCRFD Bounding Box [x1, y1, x2, y2]
                    </div>
                    <div className="font-mono font-semibold text-tf-text">
                      [{result.bounding_box.join(", ")}]
                    </div>
                  </div>
                )}

                {/* Liveness / PAD info */}
                {result && (
                  <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border text-xs space-y-1">
                    <div className="text-tf-text-muted flex items-center gap-1 text-[11px]">
                      <ShieldAlert className="w-3.5 h-3.5" /> Presentation Attack Detection (PAD)
                    </div>
                    <div className="font-semibold text-tf-text capitalize">
                      State: {result.pad_state} {result.liveness_score !== null ? `(Score: ${(result.liveness_score * 100).toFixed(1)}%)` : ""}
                    </div>
                  </div>
                )}

                {/* Standalone PAD result */}
                {padResult && (
                  <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border text-xs space-y-1">
                    <div className="font-semibold text-tf-text">Direct Liveness Output:</div>
                    <div className="text-[11px] font-mono text-tf-text-muted overflow-auto max-h-24">
                      {JSON.stringify(padResult, null, 2)}
                    </div>
                  </div>
                )}

                {/* Reason codes */}
                {result?.reason_codes && (
                  <div className="space-y-1">
                    <div className="text-[11px] font-semibold text-tf-text-muted">Decision Evidence Codes:</div>
                    <div className="flex flex-wrap gap-1">
                      {result.reason_codes.map((code) => (
                        <span key={code} className="px-2 py-0.5 bg-tf-border/50 text-tf-text rounded text-[10px] font-mono">
                          {code}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
