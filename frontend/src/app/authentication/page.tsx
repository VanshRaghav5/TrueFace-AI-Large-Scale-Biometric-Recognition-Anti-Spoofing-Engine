"use client";

import { useEffect, useRef, useState } from "react";
import VoiceWave from "@/components/VoiceWave";
import TerminalLog, { TerminalEvent } from "@/components/TerminalLog";
import CameraPreview from "@/components/CameraPreview";
import MetricDisplay from "@/components/MetricDisplay";
import StatusBadge from "@/components/StatusBadge";
import VerificationStages, { VerificationStage } from "@/components/VerificationStages";
import PipelineStepper from "@/components/PipelineStepper";
import FileDropZone from "@/components/FileDropZone";
import {
  Camera,
  Upload,
  Mic,
  Square,
  KeyRound,
  Trash2,
  RefreshCw,
  Shield,
  CheckCircle2,
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

  const [authResponse, setAuthResponse] = useState<AuthenticationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [terminalEvents, setTerminalEvents] = useState<TerminalEvent[]>([]);
  const [verificationStages, setVerificationStages] = useState<VerificationStage[]>([]);

  // Pipeline steps state
  const [pipelineSteps, setPipelineSteps] = useState<Array<{
    id: number;
    name: string;
    status: "pending" | "processing" | "success" | "failed";
  }>>([
    { id: 1, name: "Detection", status: "pending" },
    { id: 2, name: "Recognition", status: "pending" },
    { id: 3, name: "Liveness", status: "pending" },
    { id: 4, name: "Deepfake", status: "pending" },
    { id: 5, name: "Voice", status: "pending" },
    { id: 6, name: "Decision", status: "pending" },
  ]);

  // Camera
  const [useCamera, setUseCamera] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Voice recording
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

  const addEvent = (status: TerminalEvent["status"], message: string, detail?: string) => {
    setTerminalEvents((prev) => [...prev, { timestamp: new Date(), status, message, detail }]);
  };

  async function startCamera() {
    try {
      setUseCamera(true);
      addEvent("processing", "Initializing camera...");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
      addEvent("success", "Camera active", "640x480 feed");
    } catch {
      setError("Webcam access denied or unavailable.");
      addEvent("error", "Camera initialization failed", "Check permissions");
      setUseCamera(false);
    }
  }

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
    if (useCamera) {
      addEvent("info", "Camera stopped");
    }
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
        addEvent("success", "Frame captured", `${file.size} bytes`);
      }
    }, "image/jpeg", 0.95);
  }

  async function startVoiceRecording() {
    try {
      addEvent("processing", "Starting audio capture...");
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
          addEvent("success", "Audio converted to WAV", `${file.size} bytes`);
          await audioCtx.close();
        } catch {
          const file = new File([webmBlob], `voice_auth_${Date.now()}.webm`, { type: "audio/webm" });
          setVoiceSample(file);
          setVoicePreviewUrl(URL.createObjectURL(webmBlob));
          addEvent("warning", "Audio saved as WebM", "WAV conversion failed");
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      addEvent("success", "Recording started", "16kHz mono");

      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      setError("Microphone access denied or unavailable.");
      addEvent("error", "Audio capture failed", "Check permissions");
    }
  }

  function stopVoiceRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      addEvent("info", "Recording stopped", `${recordingDuration}s duration`);
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
    addEvent("info", "Voice sample discarded");
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
    setVerificationStages([]);
  }

  async function verifyFullMultimodal() {
    if (!faceImage) {
      setError("Face image is required for verification.");
      addEvent("error", "Verification blocked", "No face image provided");
      return;
    }
    setSubmitting(true);
    clearResults();
    addEvent("processing", "Starting multimodal verification...");

    // Reset pipeline steps
    setPipelineSteps([
      { id: 1, name: "Detection", status: "processing" },
      { id: 2, name: "Recognition", status: "pending" },
      { id: 3, name: "Liveness", status: "pending" },
      { id: 4, name: "Deepfake", status: "pending" },
      { id: 5, name: "Voice", status: "pending" },
      { id: 6, name: "Decision", status: "pending" },
    ]);

    const form = new FormData();
    form.append("face_image", faceImage);
    if (voiceSample) {
      form.append("voice_sample", voiceSample);
      addEvent("info", "Voice sample attached");
    }
    if (claimedId.trim()) {
      form.append("claimed_subject_id", claimedId.trim());
      addEvent("info", `Claimed ID: ${claimedId.trim()}`);
    }
    if (securityPin.trim()) {
      form.append("security_pin", securityPin.trim());
      addEvent("info", "Security PIN attached");
    }

    try {
      // Stage 1: Face Recognition
      setVerificationStages([{ stage: "face", status: "processing" }]);
      addEvent("processing", "Gate 1/6: Face recognition...");
      
      const response = await fetch(`${apiBase}/authentication/verify`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Verification failed");
      }
      setAuthResponse(payload);

      // Parse face results
      if (payload.face_result?.face_detected) {
        setPipelineSteps(prev => prev.map(s => s.id === 1 ? { ...s, status: "success" as const } : s.id === 2 ? { ...s, status: "processing" as const } : s));
        const sim = payload.face_result.identity_similarity;
        addEvent("success", "Face detected", sim ? `Similarity: ${(sim * 100).toFixed(1)}%` : "");
        setVerificationStages(prev => [
          ...prev.map(s => s.stage === "face" ? { ...s, status: "success" as const } : s),
        ]);
      } else {
        setPipelineSteps(prev => prev.map(s => s.id === 1 ? { ...s, status: "failed" as const } : s));
        addEvent("error", "No face detected");
        setVerificationStages(prev => [
          ...prev.map(s => s.stage === "face" ? { ...s, status: "failed" as const } : s),
        ]);
      }

      // Recognition
      setPipelineSteps(prev => prev.map(s => s.id === 2 ? { ...s, status: "success" as const } : s.id === 3 ? { ...s, status: "processing" as const } : s));

      if (payload.face_result?.pad_state === "real") {
        setPipelineSteps(prev => prev.map(s => s.id === 3 ? { ...s, status: "success" as const } : s.id === 4 ? { ...s, status: "processing" as const } : s));
        const score = payload.face_result.liveness_score;
        addEvent("success", "Liveness: REAL", score ? `Score: ${(score * 100).toFixed(1)}%` : "");
      } else if (payload.face_result?.pad_state === "attack") {
        setPipelineSteps(prev => prev.map(s => s.id === 3 ? { ...s, status: "failed" as const } : s));
        addEvent("error", "Liveness: SPOOF ATTACK");
      } else {
        setPipelineSteps(prev => prev.map(s => s.id === 3 ? { ...s, status: "success" as const } : s.id === 4 ? { ...s, status: "processing" as const } : s));
      }

      if (payload.face_result?.deepfake_state === "authentic") {
        setPipelineSteps(prev => prev.map(s => s.id === 4 ? { ...s, status: "success" as const } : s.id === 5 ? { ...s, status: "processing" as const } : s));
        addEvent("success", "Deepfake: AUTHENTIC");
      } else if (payload.face_result?.deepfake_state === "manipulated") {
        setPipelineSteps(prev => prev.map(s => s.id === 4 ? { ...s, status: "failed" as const } : s));
        addEvent("error", "Deepfake: MANIPULATED");
      } else {
        setPipelineSteps(prev => prev.map(s => s.id === 4 ? { ...s, status: "success" as const } : s.id === 5 ? { ...s, status: "processing" as const } : s));
      }

      // Stage 2: Voice (if provided)
      if (voiceSample && payload.voice_result?.speech_detected) {
        setPipelineSteps(prev => prev.map(s => s.id === 5 ? { ...s, status: "success" as const } : s.id === 6 ? { ...s, status: "processing" as const } : s));
        const sim = payload.voice_result.identity_similarity;
        setVerificationStages(prev => [...prev, { stage: "voice", status: "success" }]);
        addEvent("success", "Voice detected", sim ? `Similarity: ${(sim * 100).toFixed(1)}%` : "");
      } else {
        setPipelineSteps(prev => prev.map(s => s.id === 5 ? { ...s, status: "success" as const } : s.id === 6 ? { ...s, status: "processing" as const } : s));
      }

      // Stage 3: PIN (if provided)
      if (securityPin.trim()) {
        if (payload.pin_verified === true) {
          setVerificationStages(prev => [...prev, { stage: "pin", status: "success" }]);
          addEvent("success", "PIN verified");
        } else if (payload.pin_verified === false) {
          setVerificationStages(prev => [...prev, { stage: "pin", status: "failed" }]);
          addEvent("error", "PIN verification failed");
        }
      }

      // Stage 4: Final Decision
      if (payload.overall_decision === "allow") {
        setPipelineSteps(prev => prev.map(s => s.id === 6 ? { ...s, status: "success" as const } : s));
        setVerificationStages(prev => [...prev, { stage: "complete", status: "success" }]);
        addEvent("success", "AUTHORIZATION GRANTED", `Latency: ${payload.latency_ms}ms`);
      } else {
        setPipelineSteps(prev => prev.map(s => s.id === 6 ? { ...s, status: "failed" as const } : s));
        addEvent("error", `AUTHORIZATION DENIED: ${payload.overall_decision.toUpperCase()}`);
      }

    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Verification failed";
      setError(msg);
      addEvent("error", "Verification failed", msg);
      setVerificationStages(prev => 
        prev.map(s => s.status === "processing" ? { ...s, status: "failed" as const } : s)
      );
    } finally {
      setSubmitting(false);
    }
  }

  // Individual gate checks
  async function verifyFaceOnly() {
    if (!faceImage) return;
    setSubmitting(true);
    clearResults();
    addEvent("processing", "Face verification only...");

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
      
      // Create a minimal auth response for display
      setAuthResponse({
        session_id: `face_${Date.now()}`,
        claimed_subject_id: claimedId || null,
        overall_decision: payload.recognition_state === "known" ? "allow" : "block",
        fused_identity_score: payload.identity_similarity || 0,
        fused_authenticity_score: 0,
        reason_codes: payload.reason_codes || [],
        face_result: payload,
        voice_result: { status: "missing", speech_detected: false, reason_codes: [] },
        latency_ms: payload.processing_time_ms || 0,
      } as any);

      addEvent("success", "Face verification complete", 
        `Similarity: ${((payload.identity_similarity || 0) * 100).toFixed(1)}%`);
    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Face verification failed";
      setError(msg);
      addEvent("error", "Face verification failed", msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function checkLiveness() {
    if (!faceImage) return;
    setSubmitting(true);
    clearResults();
    addEvent("processing", "Liveness check only...");

    const form = new FormData();
    form.append("face_image", faceImage);

    try {
      const response = await fetch(`${apiBase}/face/pad`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Liveness check failed");
      }
      
      addEvent("success", `Liveness: ${payload.pad_state?.toUpperCase()}`, 
        `Real score: ${((payload.real_score || 0) * 100).toFixed(1)}%`);
      
      // Show result in terminal only
    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Liveness check failed";
      setError(msg);
      addEvent("error", "Liveness check failed", msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function checkDeepfake() {
    if (!faceImage) return;
    setSubmitting(true);
    clearResults();
    addEvent("processing", "Deepfake check only...");

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
      
      addEvent("success", `Deepfake: ${payload.deepfake_state?.toUpperCase()}`, 
        `Authenticity: ${((payload.authenticity_score || 0) * 100).toFixed(1)}%`);
    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Deepfake check failed";
      setError(msg);
      addEvent("error", "Deepfake check failed", msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function checkVoice() {
    if (!voiceSample) {
      setError("Voice sample required for verification.");
      addEvent("error", "Voice check blocked", "No audio provided");
      return;
    }
    setSubmitting(true);
    clearResults();
    addEvent("processing", "Voice verification only...");

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
      
      const sim = payload.identity_similarity;
      addEvent("success", "Voice verification complete", 
        sim ? `Similarity: ${(sim * 100).toFixed(1)}%` : "No match");
    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Voice check failed";
      setError(msg);
      addEvent("error", "Voice check failed", msg);
    } finally {
      setSubmitting(false);
    }
  }

  const getOverallStatus = (): "verified" | "scanning" | "denied" | "idle" => {
    if (submitting) return "scanning";
    if (!authResponse) return "idle";
    if (authResponse.overall_decision === "allow") return "verified";
    return "denied";
  };

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-tf-surface border border-tf-border flex items-center justify-center">
              <Shield className="w-6 h-6 text-tf-accent" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">MULTIMODAL BIOMETRIC VERIFICATION</h1>
              <p className="text-xs text-gray-500 font-mono mt-1">6-GATE ZERO-TRUST AUTHENTICATION SYSTEM</p>
            </div>
          </div>
          <StatusBadge status={getOverallStatus()} />
        </div>
      </div>

      {/* Main asymmetric layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT: Large camera feed */}
        <div className="lg:col-span-2 space-y-6">
          <div className="panel p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-mono uppercase tracking-wider text-gray-400">Primary Sensor Input</h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (useCamera) stopCamera();
                    setUseCamera(false);
                  }}
                  className={`btn-secondary text-xs ${!useCamera ? "ring-1 ring-tf-accent" : ""}`}
                >
                  <Upload className="w-3 h-3" /> Upload
                </button>
                <button
                  type="button"
                  onClick={startCamera}
                  className={`btn-secondary text-xs ${useCamera ? "ring-1 ring-tf-accent" : ""}`}
                >
                  <Camera className="w-3 h-3" /> Live Camera
                </button>
              </div>
            </div>

            {useCamera ? (
              <CameraPreview
                videoRef={videoRef}
                isActive={cameraActive}
                isScanning={submitting}
                onCapture={captureFrame}
                onStop={() => {
                  stopCamera();
                  setUseCamera(false);
                }}
              />
            ) : (
              <FileDropZone
                accept="image/jpeg,image/png,image/webp"
                onFileSelect={(file) => {
                  setFaceImage(file);
                  setPreview(URL.createObjectURL(file));
                  addEvent("info", "Face image uploaded", file.name);
                }}
                currentFile={faceImage}
              />
            )}
          </div>

          {/* Voice & PIN inputs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Voice input */}
            <div className="panel p-6">
              <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <Mic className="w-4 h-4 text-tf-accent" /> Voice Biometric
              </h3>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      if (isRecording) stopVoiceRecording();
                      setUseVoiceRecorder(false);
                    }}
                    className={`btn-secondary text-xs flex-1 ${!useVoiceRecorder ? "ring-1 ring-tf-accent" : ""}`}
                  >
                    <Upload className="w-3 h-3" /> Upload
                  </button>
                  <button
                    type="button"
                    onClick={() => setUseVoiceRecorder(true)}
                    className={`btn-secondary text-xs flex-1 ${useVoiceRecorder ? "ring-1 ring-tf-accent" : ""}`}
                  >
                    <Mic className="w-3 h-3" /> Record
                  </button>
                </div>

                {useVoiceRecorder ? (
                  <div className="panel p-6">
                    <div className="flex flex-col items-center space-y-4">
                      {isRecording ? (
                        <>
                          <div className="relative w-full">
                            <VoiceWave isRecording={isRecording} className="h-24" />
                            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                              <div className="w-12 h-12 bg-tf-alert/20 border border-tf-alert flex items-center justify-center animate-pulse">
                                <Mic className="w-6 h-6 text-tf-alert" />
                              </div>
                            </div>
                          </div>
                          <div className="text-xl font-mono font-bold text-tf-alert telemetry">{formatDuration(recordingDuration)}</div>
                          <button
                            type="button"
                            onClick={stopVoiceRecording}
                            className="btn-secondary bg-tf-alert/10 border-tf-alert/30 hover:bg-tf-alert/20 text-tf-alert text-xs"
                          >
                            <Square className="w-3 h-3" /> Stop
                          </button>
                        </>
                      ) : voiceSample && voicePreviewUrl ? (
                        <>
                          <CheckCircle2 className="w-10 h-10 text-tf-accent" />
                          <p className="text-xs font-mono text-tf-accent">RECORDED ({formatDuration(recordingDuration)})</p>
                          <audio controls src={voicePreviewUrl} className="w-full" />
                          <div className="flex gap-2 w-full">
                            <button
                              type="button"
                              onClick={clearVoiceRecording}
                              className="btn-secondary flex-1 text-xs"
                            >
                              <Trash2 className="w-3 h-3" /> Discard
                            </button>
                            <button
                              type="button"
                              onClick={() => { clearVoiceRecording(); startVoiceRecording(); }}
                              className="btn-secondary flex-1 text-xs"
                            >
                              <RefreshCw className="w-3 h-3" /> Re-record
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <Mic className="w-10 h-10 text-gray-700" />
                          <button
                            type="button"
                            onClick={startVoiceRecording}
                            className="btn-primary text-xs"
                          >
                            <Mic className="w-3 h-3" /> Start Recording
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <FileDropZone
                    accept="audio/wav,audio/x-wav"
                    onFileSelect={(file) => {
                      setVoiceSample(file);
                      setVoicePreviewUrl(null);
                      addEvent("info", "Voice sample uploaded", file.name);
                    }}
                    currentFile={voiceSample}
                  />
                )}
              </div>
            </div>

            {/* Claimed ID & PIN */}
            <div className="panel p-6">
              <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-tf-accent" /> Credentials
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-2 font-mono uppercase tracking-wider">
                    Claimed Identity
                  </label>
                  <input
                    value={claimedId}
                    onChange={(e) => setClaimedId(e.target.value)}
                    placeholder="Subject ID"
                    className="w-full bg-dark border border-gray-800 px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-accent transition-colors placeholder:text-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-2 font-mono uppercase tracking-wider">
                    Security PIN
                  </label>
                  <input
                    type="password"
                    value={securityPin}
                    onChange={(e) => setSecurityPin(e.target.value)}
                    placeholder="••••••"
                    className="w-full bg-dark border border-gray-800 px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-accent transition-colors placeholder:text-gray-600"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-3">
            <button
              onClick={verifyFullMultimodal}
              disabled={!faceImage || submitting}
              className="btn-primary w-full !py-4 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <Shield className="w-5 h-5" />
              {submitting ? "VERIFYING ALL GATES..." : "INITIATE FULL VERIFICATION"}
            </button>

            {/* Individual Gate Checks */}
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={verifyFaceOnly}
                disabled={!faceImage || submitting}
                className="btn-secondary text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Face Match
              </button>
              <button
                onClick={checkLiveness}
                disabled={!faceImage || submitting}
                className="btn-secondary text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anti-Spoof
              </button>
              <button
                onClick={checkDeepfake}
                disabled={!faceImage || submitting}
                className="btn-secondary text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Deepfake Check
              </button>
              <button
                onClick={checkVoice}
                disabled={!voiceSample || submitting}
                className="btn-secondary text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Voice Verify
              </button>
            </div>
          </div>

          {error && (
            <div className="panel p-4 bg-tf-alert/10 border-tf-alert text-tf-alert">
              <p className="text-xs font-mono">{error}</p>
            </div>
          )}
        </div>

        {/* RIGHT: Stacked metrics and event log */}
        <div className="space-y-6">
          {/* 6-Gate Pipeline Progress */}
          {submitting && (
            <PipelineStepper steps={pipelineSteps} />
          )}

          {/* Verification Stage Animation */}
          {verificationStages.length > 0 && (
            <VerificationStages stages={verificationStages} />
          )}

          {/* Metrics */}
          {authResponse && (
            <div className="space-y-4">
              <MetricDisplay
                label="IDENTITY MATCH"
                value={((authResponse.fused_identity_score ?? 0) * 100).toFixed(1)}
                unit="%"
                status={(authResponse.fused_identity_score ?? 0) > 0.7 ? "success" : (authResponse.fused_identity_score ?? 0) > 0.4 ? "warning" : "error"}
              />
              <MetricDisplay
                label="AUTHENTICITY SCORE"
                value={((authResponse.fused_authenticity_score ?? 0) * 100).toFixed(1)}
                unit="%"
                status={(authResponse.fused_authenticity_score ?? 0) > 0.5 ? "success" : "warning"}
              />
              <MetricDisplay
                label="PROCESSING TIME"
                value={authResponse.latency_ms}
                unit="ms"
                status="neutral"
              />
            </div>
          )}

          {/* Terminal Log */}
          <TerminalLog events={terminalEvents} maxHeight="32rem" />
        </div>
      </div>
    </div>
  );
}
