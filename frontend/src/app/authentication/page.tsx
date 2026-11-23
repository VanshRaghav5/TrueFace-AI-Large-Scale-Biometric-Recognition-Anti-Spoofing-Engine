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
  Mic,
  MicOff,
  Square,
  KeyRound,
  CheckCircle2,
  XCircle,
  Eye,
  Activity,
  Layers,
  Trash2,
  RefreshCw,
} from "lucide-react";

interface FaceResultData {
  status: string;
  face_detected: boolean;
  bounding_box: [number, number, number, number] | null;
  identity: string | null;
  recognition_state: string;
  identity_similarity: number | null;
  model_name: string;
  providers: string[];
  processing_time_ms: number;
  liveness_score: number | null;
  pad_spoof_score: number | null;
  pad_state: string;
  pad_provider: string | null;
  deepfake_score?: number | null;
  deepfake_manipulation_score?: number | null;
  deepfake_state?: string | null;
  deepfake_provider?: string | null;
  reason_codes: string[];
}

interface GateStatus {
  passed: boolean;
  status: string;
  detail?: string | null;
}

interface AuthenticationResponse {
  session_id: string;
  claimed_subject_id: string | null;
  overall_decision: "allow" | "step_up" | "block" | "error";
  fused_identity_score: number;
  fused_authenticity_score: number;
  reason_codes: string[];
  face_result: FaceResultData;
  voice_result: {
    status: string;
    speech_detected: boolean;
    identity_similarity: number | null;
    antispoof_score: number | null;
    reason_codes: string[];
  };
  gates?: {
    face_recognition: GateStatus;
    liveness_anti_spoof: GateStatus;
    deepfake_detection: GateStatus;
    voice_recognition: GateStatus;
    voice_anti_spoof: GateStatus;
    security_pin: GateStatus;
  };
  pin_verified?: boolean | null;
  latency_ms: number;
}

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export default function AuthenticationPage() {
  const [claimedId, setClaimedId] = useState("");
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [securityPin, setSecurityPin] = useState("");
  const [preview, setPreview] = useState<string | null>(null);

  // Results
  const [authResponse, setAuthResponse] = useState<AuthenticationResponse | null>(null);
  const [result, setResult] = useState<FaceResultData | null>(null);
  const [padResult, setPadResult] = useState<Record<string, unknown> | null>(null);
  const [deepfakeResult, setDeepfakeResult] = useState<Record<string, unknown> | null>(null);
  const [voiceResult, setVoiceResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [activeAction, setActiveAction] = useState<string>("");

  // Camera handling
  const [useCamera, setUseCamera] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Voice recording state
  const [useVoiceRecorder, setUseVoiceRecorder] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [voicePreviewUrl, setVoicePreviewUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      stopCamera();
      stopVoiceRecording();
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

  async function startVoiceRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      audioStreamRef.current = stream;
      audioChunksRef.current = [];
      setRecordingDuration(0);

      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const webmBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        try {
          const arrayBuffer = await webmBlob.arrayBuffer();
          const audioCtx = new AudioContext({ sampleRate: 16000 });
          const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
          const wavBlob = audioBufferToWav(audioBuffer);
          const file = new File([wavBlob], `voice_auth_${Date.now()}.wav`, { type: "audio/wav" });
          setVoiceSample(file);
          setVoicePreviewUrl(URL.createObjectURL(wavBlob));
          await audioCtx.close();
        } catch {
          const file = new File([webmBlob], `voice_auth_${Date.now()}.webm`, { type: "audio/webm" });
          setVoiceSample(file);
          setVoicePreviewUrl(URL.createObjectURL(webmBlob));
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);

      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      setError("Microphone access denied or unavailable.");
    }
  }

  function stopVoiceRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    setIsRecording(false);
  }

  function clearVoiceRecording() {
    stopVoiceRecording();
    setVoiceSample(null);
    setVoicePreviewUrl(null);
    setRecordingDuration(0);
  }

  function formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  function audioBufferToWav(buffer: AudioBuffer): Blob {
    const numChannels = 1;
    const sampleRate = buffer.sampleRate;
    const format = 1;
    const bitsPerSample = 16;
    const channelData = buffer.getChannelData(0);
    const dataLength = channelData.length * (bitsPerSample / 8);
    const headerLength = 44;
    const totalLength = headerLength + dataLength;
    const arrayBuffer = new ArrayBuffer(totalLength);
    const view = new DataView(arrayBuffer);

    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };
    writeString(0, "RIFF");
    view.setUint32(4, totalLength - 8, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, format, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * (bitsPerSample / 8), true);
    view.setUint16(32, numChannels * (bitsPerSample / 8), true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, "data");
    view.setUint32(40, dataLength, true);

    let offset = 44;
    for (let i = 0; i < channelData.length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }

    return new Blob([arrayBuffer], { type: "audio/wav" });
  }

  function clearResults() {
    setError(null);
    setAuthResponse(null);
    setResult(null);
    setPadResult(null);
    setDeepfakeResult(null);
    setVoiceResult(null);
  }

  // 1. Full Multimodal Zero-Trust Verification (All 6 Gates)
  async function verifyFullMultimodal() {
    if (!faceImage) {
      setError("Face image is required for multimodal verification.");
      return;
    }
    setSubmitting(true);
    setActiveAction("multimodal");
    clearResults();

    const form = new FormData();
    form.append("face_image", faceImage);
    if (voiceSample) {
      form.append("voice_sample", voiceSample);
    }
    if (claimedId.trim()) {
      form.append("claimed_subject_id", claimedId.trim());
    }
    if (securityPin.trim()) {
      form.append("security_pin", securityPin.trim());
    }

    try {
      const response = await fetch(`${apiBase}/authentication/verify`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Multimodal verification failed");
      }
      setAuthResponse(payload);
      setResult(payload.face_result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Multimodal verification failed");
    } finally {
      setSubmitting(false);
      setActiveAction("");
    }
  }

  // 2. Direct Face Verification (ArcFace + PAD + Deepfake)
  async function verifyFaceOnly() {
    if (!faceImage) return;
    setSubmitting(true);
    setActiveAction("face");
    clearResults();

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
      setActiveAction("");
    }
  }

  // 3. Standalone PAD
  async function checkLiveness() {
    if (!faceImage) return;
    setSubmitting(true);
    setActiveAction("pad");
    clearResults();

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
      setActiveAction("");
    }
  }

  // 4. Standalone Deepfake Check (DeepfakeBench)
  async function checkDeepfake() {
    if (!faceImage) return;
    setSubmitting(true);
    setActiveAction("deepfake");
    clearResults();

    const form = new FormData();
    form.append("face_image", faceImage);

    try {
      const response = await fetch(`${apiBase}/face/deepfake`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Deepfake check failed");
      }
      setDeepfakeResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Deepfake check failed");
    } finally {
      setSubmitting(false);
      setActiveAction("");
    }
  }

  // 5. Standalone Voice Check
  async function checkVoice() {
    if (!voiceSample) {
      setError("Please select a .wav audio sample to run voice verification.");
      return;
    }
    setSubmitting(true);
    setActiveAction("voice");
    clearResults();

    const form = new FormData();
    form.append("voice_sample", voiceSample);
    if (claimedId.trim()) {
      form.append("claimed_subject_id", claimedId.trim());
    }

    try {
      const response = await fetch(`${apiBase}/voice/verify`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Voice check failed");
      }
      setVoiceResult(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Voice check failed");
    } finally {
      setSubmitting(false);
      setActiveAction("");
    }
  }

  const isSpoofAttack = result?.pad_state === "attack" || result?.recognition_state === "spoof_attack_detected";
  const isDeepfakeDetected = result?.deepfake_state === "manipulated" || result?.recognition_state === "deepfake_detected";
  const isFaceMatched = !isSpoofAttack && !isDeepfakeDetected && result?.recognition_state === "known" && Boolean(result?.identity);
  const similarityScore = result?.identity_similarity !== null && result?.identity_similarity !== undefined
    ? Number(result.identity_similarity)
    : null;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Multimodal Zero-Trust Biometric Security</h1>
        <p className="text-sm text-tf-text-muted mt-1">
          Sequential multi-barrier verification: Face Recognition (ArcFace) → Liveness & Anti-Spoof (MiniFASNet) → Deepfake Detection (DeepfakeBench) → Voice Recognition → Audio Anti-Spoof → Secret PIN Code.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input Card (5 columns) */}
        <div className="lg:col-span-5 border border-tf-border rounded-card bg-tf-surface p-5 space-y-5 shadow-sm">
          <h2 className="text-sm font-semibold text-tf-text flex items-center gap-2 border-b border-tf-border pb-2.5">
            <Layers className="w-4 h-4 text-tf-primary" /> Credentials & Media Input
          </h2>

          {/* Claimed Subject ID */}
          <div className="space-y-1">
            <label className="block text-xs font-semibold text-tf-text">
              Claimed Identity ID <span className="text-[11px] text-tf-text-muted font-normal">(Optional for 1:N gallery)</span>
            </label>
            <input
              value={claimedId}
              onChange={(e) => setClaimedId(e.target.value)}
              placeholder="e.g. Vansh or subj_1001"
              className="block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-xs focus:outline-none focus:border-tf-primary"
            />
          </div>

          {/* Face Source */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-tf-text flex items-center gap-1.5">
              <Camera className="w-3.5 h-3.5 text-tf-primary" /> 1. Face Input (Required)
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  if (useCamera) stopCamera();
                  setUseCamera(false);
                }}
                className={`flex-1 py-1.5 px-2 rounded-input text-xs font-medium border flex items-center justify-center gap-1 transition-colors ${
                  !useCamera
                    ? "bg-tf-primary text-white border-tf-primary"
                    : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                }`}
              >
                <Upload className="w-3 h-3" /> Upload File
              </button>
              <button
                type="button"
                onClick={startCamera}
                className={`flex-1 py-1.5 px-2 rounded-input text-xs font-medium border flex items-center justify-center gap-1 transition-colors ${
                  useCamera
                    ? "bg-tf-primary text-white border-tf-primary"
                    : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                }`}
              >
                <Camera className="w-3 h-3" /> Live Camera
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
                    className="w-full py-1.5 bg-emerald-600 text-white rounded-input text-xs font-medium flex items-center justify-center gap-1.5"
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
                  className="block w-full text-xs text-tf-text-muted file:mr-2 file:py-1 file:px-2.5 file:rounded-input file:border-0 file:text-xs file:font-medium file:bg-tf-surface-muted file:text-tf-text hover:file:bg-tf-border"
                />
              </div>
            )}

            {preview && (
              <div className="rounded-input overflow-hidden border border-tf-border bg-tf-surface-muted p-1">
                <img src={preview} alt="Selected face preview" className="max-h-32 w-full rounded-input object-contain" />
              </div>
            )}
          </div>

          {/* Voice Sample Input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-tf-text flex items-center gap-1.5">
              <Mic className="w-3.5 h-3.5 text-tf-primary" /> 2. Voice Audio Sample
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  if (isRecording) stopVoiceRecording();
                  setUseVoiceRecorder(false);
                }}
                className={`flex-1 py-1.5 px-2 rounded-input text-xs font-medium border flex items-center justify-center gap-1 transition-colors ${
                  !useVoiceRecorder
                    ? "bg-tf-primary text-white border-tf-primary"
                    : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                }`}
              >
                <Upload className="w-3 h-3" /> Upload .wav
              </button>
              <button
                type="button"
                onClick={() => setUseVoiceRecorder(true)}
                className={`flex-1 py-1.5 px-2 rounded-input text-xs font-medium border flex items-center justify-center gap-1 transition-colors ${
                  useVoiceRecorder
                    ? "bg-tf-primary text-white border-tf-primary"
                    : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                }`}
              >
                <Mic className="w-3 h-3" /> Live Record
              </button>
            </div>

            {useVoiceRecorder ? (
              <div className="space-y-2">
                <div className="relative rounded-input overflow-hidden bg-tf-surface-muted border border-tf-border p-3">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    {isRecording ? (
                      <>
                        <div className="relative">
                          <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center animate-pulse">
                            <Mic className="w-6 h-6 text-red-600" />
                          </div>
                          <div className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-red-500 animate-ping" />
                        </div>
                        <div className="text-xs font-mono font-bold text-red-600">{formatDuration(recordingDuration)}</div>
                        <p className="text-[10px] text-tf-text-muted">Speak clearly into your microphone</p>
                        <button
                          type="button"
                          onClick={stopVoiceRecording}
                          className="py-1.5 px-4 bg-red-600 text-white rounded-input text-[11px] font-medium flex items-center gap-1 hover:bg-red-700 transition-colors"
                        >
                          <Square className="w-3 h-3" /> Stop
                        </button>
                      </>
                    ) : voiceSample && voicePreviewUrl ? (
                      <>
                        <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                          <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                        </div>
                        <p className="text-[11px] font-semibold text-emerald-700">Recorded ({formatDuration(recordingDuration)})</p>
                        <audio controls src={voicePreviewUrl} className="w-full max-w-[220px] h-8" />
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={clearVoiceRecording}
                            className="py-1 px-3 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors"
                          >
                            <Trash2 className="w-3 h-3 inline mr-1" /> Discard
                          </button>
                          <button
                            type="button"
                            onClick={() => { clearVoiceRecording(); startVoiceRecording(); }}
                            className="py-1 px-3 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors"
                          >
                            <RefreshCw className="w-3 h-3 inline mr-1" /> Redo
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="w-12 h-12 rounded-full bg-tf-surface flex items-center justify-center border-2 border-dashed border-tf-border">
                          <Mic className="w-6 h-6 text-tf-text-muted" />
                        </div>
                        <button
                          type="button"
                          onClick={startVoiceRecording}
                          className="py-1.5 px-4 bg-tf-primary text-white rounded-input text-[11px] font-medium flex items-center gap-1 hover:bg-tf-primary-hover transition-colors"
                        >
                          <Mic className="w-3 h-3" /> Start Recording
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  accept="audio/wav,audio/x-wav"
                  onChange={(e) => { setVoiceSample(e.target.files?.[0] ?? null); setVoicePreviewUrl(null); }}
                  className="block w-full text-xs text-tf-text-muted file:mr-2 file:py-1 file:px-2.5 file:rounded-input file:border-0 file:text-xs file:font-medium file:bg-tf-surface-muted file:text-tf-text hover:file:bg-tf-border"
                />
                {voiceSample && (
                  <div className="text-[11px] text-emerald-600 font-mono mt-1">Loaded: {voiceSample.name}</div>
                )}
              </div>
            )}
          </div>

          {/* Security PIN Input */}
          <div className="space-y-1">
            <label className="block text-xs font-semibold text-tf-text flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-tf-primary" /> 3. Final Security PIN / Secret Code
            </label>
            <input
              type="password"
              value={securityPin}
              onChange={(e) => setSecurityPin(e.target.value)}
              placeholder="Enter user-configured secret PIN"
              className="block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-xs focus:outline-none focus:border-tf-primary"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 pt-2 border-t border-tf-border">
            <button
              onClick={verifyFullMultimodal}
              disabled={!faceImage || submitting}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-tf-surface-muted disabled:text-tf-text-muted text-white rounded-input text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors shadow-sm"
            >
              <ShieldCheck className="w-4 h-4" />
              {submitting && activeAction === "multimodal" ? "Verifying All 6 Gates..." : "Verify All 6 Security Gates"}
            </button>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={verifyFaceOnly}
                disabled={!faceImage || submitting}
                className="py-1.5 px-2 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors disabled:opacity-50"
              >
                {submitting && activeAction === "face" ? "Processing..." : "Face Match (ArcFace)"}
              </button>
              <button
                onClick={checkLiveness}
                disabled={!faceImage || submitting}
                className="py-1.5 px-2 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors disabled:opacity-50"
              >
                {submitting && activeAction === "pad" ? "Testing..." : "Anti-Spoof (PAD)"}
              </button>
              <button
                onClick={checkDeepfake}
                disabled={!faceImage || submitting}
                className="py-1.5 px-2 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors disabled:opacity-50"
              >
                {submitting && activeAction === "deepfake" ? "Scanning..." : "Deepfake Check"}
              </button>
              <button
                onClick={checkVoice}
                disabled={!voiceSample || submitting}
                className="py-1.5 px-2 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-[11px] font-medium transition-colors disabled:opacity-50"
              >
                {submitting && activeAction === "voice" ? "Analyzing..." : "Voice & Audio Check"}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-800 border border-red-200 rounded-input text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Results Card (7 columns) */}
        <div className="lg:col-span-7 border border-tf-border rounded-card bg-tf-surface p-5 space-y-5 shadow-sm">
          <div>
            <h2 className="text-sm font-semibold text-tf-text border-b border-tf-border pb-2.5 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-tf-primary" /> Security Verification Forensics
              </span>
              {(authResponse || result || padResult || deepfakeResult || voiceResult) && (
                <button onClick={clearResults} className="text-[11px] text-tf-text-muted hover:text-tf-text">
                  Clear
                </button>
              )}
            </h2>

            {!authResponse && !result && !padResult && !deepfakeResult && !voiceResult ? (
              <div className="py-24 text-center text-xs text-tf-text-muted space-y-2">
                <ShieldCheck className="w-10 h-10 mx-auto text-tf-text-muted/40 stroke-1" />
                <p>Provide face image and optional credentials, then click <strong>"Verify All 6 Security Gates"</strong>.</p>
                <p className="text-[11px]">System validates Face ID → Liveness → Deepfake → Voice → Audio Spoof → Secret PIN.</p>
              </div>
            ) : (
              <div className="space-y-4 pt-3">
                {/* 1. Full Multimodal Decision Banner */}
                {authResponse && (
                  <div
                    className={`p-4 rounded-card border flex items-center justify-between transition-all ${
                      authResponse.overall_decision === "allow"
                        ? "bg-emerald-50 border-emerald-300 text-emerald-950 dark:bg-emerald-950/40 dark:border-emerald-900"
                        : "bg-red-50 border-red-300 text-red-950 dark:bg-red-950/40 dark:border-red-900"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {authResponse.overall_decision === "allow" ? (
                        <div className="w-11 h-11 rounded-full bg-emerald-600 text-white flex items-center justify-center flex-shrink-0">
                          <CheckCircle2 className="w-7 h-7" />
                        </div>
                      ) : (
                        <div className="w-11 h-11 rounded-full bg-red-600 text-white flex items-center justify-center flex-shrink-0 animate-pulse">
                          <XCircle className="w-7 h-7" />
                        </div>
                      )}
                      <div>
                        <div className="text-sm font-bold uppercase tracking-wider">
                          {authResponse.overall_decision === "allow"
                            ? "ACCESS GRANTED — ALL 6 GATES VERIFIED"
                            : "ACCESS BLOCKED — SECURITY GATE FAILURE"}
                        </div>
                        <div className="text-xs font-semibold mt-0.5">
                          {authResponse.overall_decision === "allow"
                            ? `Subject Verified: ${authResponse.claimed_subject_id ?? "Authenticated"} | Fused Trust: ${(authResponse.fused_authenticity_score * 100).toFixed(1)}%`
                            : "Zero-Trust policy violation: One or more security barriers were breached."}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Zero-Trust 6-Gate Checklist Matrix */}
                {authResponse?.gates && (
                  <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border space-y-2">
                    <div className="text-xs font-bold text-tf-text uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-tf-primary" /> Multi-Barrier Zero-Trust Checklist
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs pt-1">
                      {/* Gate 1 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.face_recognition.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">1. Face Recognition</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.face_recognition.detail ?? "ArcFace match"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.face_recognition.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.face_recognition.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>

                      {/* Gate 2 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.liveness_anti_spoof.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">2. Anti-Spoof (PAD)</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.liveness_anti_spoof.detail ?? "MiniFASNet"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.liveness_anti_spoof.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.liveness_anti_spoof.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>

                      {/* Gate 3 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.deepfake_detection.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">3. Deepfake Check</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.deepfake_detection.detail ?? "DeepfakeBench"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.deepfake_detection.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.deepfake_detection.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>

                      {/* Gate 4 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.voice_recognition.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">4. Voice Match</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.voice_recognition.detail ?? "Speaker similarity"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.voice_recognition.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.voice_recognition.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>

                      {/* Gate 5 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.voice_anti_spoof.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">5. Voice Anti-Spoof</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.voice_anti_spoof.detail ?? "Synthetic speech check"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.voice_anti_spoof.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.voice_anti_spoof.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>

                      {/* Gate 6 */}
                      <div className={`p-2 rounded border flex items-start justify-between ${
                        authResponse.gates.security_pin.passed ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50/70 border-red-200"
                      }`}>
                        <div>
                          <div className="font-semibold text-tf-text">6. Secret PIN Code</div>
                          <div className="text-[11px] text-tf-text-muted">{authResponse.gates.security_pin.detail ?? "Passcode hash match"}</div>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          authResponse.gates.security_pin.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                        }`}>
                          {authResponse.gates.security_pin.passed ? "PASSED" : "BLOCKED"}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Deepfake Detection Card (DeepfakeBench) */}
                {(result?.deepfake_score !== undefined || deepfakeResult) && (
                  <div className={`p-3 rounded-input border text-xs space-y-2 ${
                    isDeepfakeDetected || (deepfakeResult && deepfakeResult.is_deepfake)
                      ? "bg-red-50 border-red-300 dark:bg-red-950/20"
                      : "bg-tf-surface-muted border-tf-border"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-tf-text flex items-center gap-1.5">
                        <Eye className="w-4 h-4 text-tf-primary" />
                        DeepfakeBench Facial Manipulation Analysis
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        isDeepfakeDetected || (deepfakeResult && deepfakeResult.is_deepfake)
                          ? "bg-red-100 text-red-800 border border-red-300 animate-pulse"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      }`}>
                        {isDeepfakeDetected || (deepfakeResult && deepfakeResult.is_deepfake)
                          ? "Deepfake Detected"
                          : "Authentic Face"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <div className="p-2 bg-white/60 dark:bg-black/20 rounded border border-tf-border/50">
                        <div className="text-[10px] text-tf-text-muted">Authenticity Probability</div>
                        <div className="text-sm font-mono font-bold text-emerald-600">
                          {((result?.deepfake_score ?? (deepfakeResult?.authenticity_score as number ?? 0)) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="p-2 bg-white/60 dark:bg-black/20 rounded border border-tf-border/50">
                        <div className="text-[10px] text-tf-text-muted">Manipulation Probability</div>
                        <div className={`text-sm font-mono font-bold ${
                          (result?.deepfake_manipulation_score ?? (deepfakeResult?.manipulation_score as number ?? 0)) > 0.4
                            ? "text-red-600"
                            : "text-tf-text-muted"
                        }`}>
                          {((result?.deepfake_manipulation_score ?? (deepfakeResult?.manipulation_score as number ?? 0)) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Presentation Attack Detection (Silent-Face MiniFASNet) */}
                {(result?.liveness_score !== undefined || padResult) && (
                  <div className={`p-3 rounded-input border text-xs space-y-2 ${
                    isSpoofAttack || (padResult && padResult.pad_state === "attack")
                      ? "bg-red-50 border-red-300 dark:bg-red-950/20"
                      : "bg-tf-surface-muted border-tf-border"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-tf-text flex items-center gap-1.5">
                        <ShieldAlert className="w-4 h-4 text-tf-primary" />
                        Silent-Face Anti-Spoofing (MiniFASNet Ensemble)
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        isSpoofAttack || (padResult && padResult.pad_state === "attack")
                          ? "bg-red-100 text-red-800 border border-red-300 animate-pulse"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      }`}>
                        {isSpoofAttack || (padResult && padResult.pad_state === "attack") ? "Spoof Attack" : "Live Face"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <div className="p-2 bg-white/60 dark:bg-black/20 rounded border border-tf-border/50">
                        <div className="text-[10px] text-tf-text-muted">Bona Fide Liveness</div>
                        <div className="text-sm font-mono font-bold text-emerald-600">
                          {((result?.liveness_score ?? (padResult?.real_score as number ?? 0)) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="p-2 bg-white/60 dark:bg-black/20 rounded border border-tf-border/50">
                        <div className="text-[10px] text-tf-text-muted">Spoof Probability</div>
                        <div className={`text-sm font-mono font-bold ${
                          (result?.pad_spoof_score ?? (padResult?.spoof_score as number ?? 0)) > 0.4
                            ? "text-red-600"
                            : "text-tf-text-muted"
                        }`}>
                          {((result?.pad_spoof_score ?? (padResult?.spoof_score as number ?? 0)) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5. Voice Biometrics Result */}
                {voiceResult && (
                  <div className="p-3 bg-tf-surface-muted rounded-input border border-tf-border text-xs space-y-2">
                    <div className="font-semibold text-tf-text flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Mic className="w-4 h-4 text-tf-primary" /> Voice Verification & Anti-Spoof
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        (voiceResult.antispoof_score as number ?? 0) >= 0.80 ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                      }`}>
                        {(voiceResult.antispoof_score as number ?? 0) >= 0.80 ? "Human Speech" : "Synthetic/Spoof"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <div>Similarity: <span className="font-mono font-bold">{voiceResult.identity_similarity !== null ? `${((voiceResult.identity_similarity as number) * 100).toFixed(1)}%` : "N/A"}</span></div>
                      <div>Speech Genuine: <span className="font-mono font-bold">{voiceResult.antispoof_score !== null ? `${((voiceResult.antispoof_score as number) * 100).toFixed(1)}%` : "N/A"}</span></div>
                    </div>
                  </div>
                )}

                {/* 6. Reason Codes */}
                {(authResponse?.reason_codes || result?.reason_codes) && (
                  <div className="space-y-1 pt-1">
                    <div className="text-[11px] font-semibold text-tf-text-muted">Evidence & Audit Codes:</div>
                    <div className="flex flex-wrap gap-1">
                      {(authResponse?.reason_codes ?? result?.reason_codes ?? []).map((code) => (
                        <span key={code} className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                          code.includes("ATTACK") || code.includes("SPOOF") || code.includes("MISMATCH") || code.includes("BLOCKED")
                            ? "bg-red-100 text-red-800 border border-red-200"
                            : code.includes("MATCH") || code.includes("AUTHENTIC") || code.includes("BONA_FIDE")
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                            : "bg-tf-border/50 text-tf-text"
                        }`}>
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
