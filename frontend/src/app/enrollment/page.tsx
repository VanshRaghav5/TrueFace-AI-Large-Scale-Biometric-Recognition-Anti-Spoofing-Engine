"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import VoiceWave from "@/components/VoiceWave";
import { UserPlus, ShieldAlert, Camera, Upload, Trash2, CheckCircle2, AlertCircle, RefreshCw, Mic, Square, Users } from "lucide-react";
import FileDropZone from "@/components/FileDropZone";

interface EnrolledItem {
  subject_id: string;
  consent_granted: boolean;
  created_at: string;
}

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export default function EnrollmentPage() {
  const [consent, setConsent] = useState(false);
  const [subjectId, setSubjectId] = useState("");
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [securityPin, setSecurityPin] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Camera state
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

  // Registered subjects
  const [enrolledSubjects, setEnrolledSubjects] = useState<EnrolledItem[]>([]);
  const [loadingSubjects, setLoadingSubjects] = useState(false);

  useEffect(() => {
    fetchEnrolledSubjects();
    return () => {
      stopCamera();
      stopVoiceRecording();
    };
  }, []);

  async function fetchEnrolledSubjects() {
    setLoadingSubjects(true);
    try {
      const res = await fetch(`${apiBase}/enrollment`);
      if (res.ok) {
        const data = await res.json();
        setEnrolledSubjects(data.items ?? []);
      }
    } catch {
      // Backend might be offline
    } finally {
      setLoadingSubjects(false);
    }
  }

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
      setMessage({ text: "Camera access was denied or is not available.", type: "error" });
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

  function capturePhoto() {
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
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
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
        // Convert webm to wav using AudioContext for backend compatibility
        try {
          const arrayBuffer = await webmBlob.arrayBuffer();
          const audioCtx = new AudioContext({ sampleRate: 16000 });
          const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
          const wavBlob = audioBufferToWav(audioBuffer);
          const file = new File([wavBlob], `voice_recording_${Date.now()}.wav`, { type: "audio/wav" });
          setVoiceSample(file);
          setVoicePreviewUrl(URL.createObjectURL(wavBlob));
          await audioCtx.close();
        } catch {
          // Fallback: send webm as-is if wav conversion fails
          const file = new File([webmBlob], `voice_recording_${Date.now()}.webm`, { type: "audio/webm" });
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
      setMessage({ text: "Microphone access was denied or is not available.", type: "error" });
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

  // Convert AudioBuffer to WAV Blob (PCM 16-bit mono)
  function audioBufferToWav(buffer: AudioBuffer): Blob {
    const numChannels = 1;
    const sampleRate = buffer.sampleRate;
    const format = 1; // PCM
    const bitsPerSample = 16;
    const channelData = buffer.getChannelData(0);
    const dataLength = channelData.length * (bitsPerSample / 8);
    const headerLength = 44;
    const totalLength = headerLength + dataLength;
    const arrayBuffer = new ArrayBuffer(totalLength);
    const view = new DataView(arrayBuffer);

    // WAV header
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

    // PCM samples
    let offset = 44;
    for (let i = 0; i < channelData.length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }

    return new Blob([arrayBuffer], { type: "audio/wav" });
  }

  async function submitEnrollment() {
    if (!subjectId.trim() || !faceImage || !consent) return;
    setSubmitting(true);
    setMessage(null);

    const form = new FormData();
    form.append("subject_id", subjectId.trim());
    form.append("consent_confirmed", "true");
    form.append("face_image", faceImage);
    if (voiceSample) {
      form.append("voice_sample", voiceSample);
    }
    if (securityPin.trim()) {
      form.append("security_pin", securityPin.trim());
    }

    try {
      const response = await fetch(`${apiBase}/enrollment`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Enrollment failed");
      }

      setMessage({
        text: `Subject "${subjectId}" successfully enrolled! (${payload.detail ?? "Credentials saved"})`,
        type: "success",
      });
      setSubjectId("");
      setFaceImage(null);
      setVoiceSample(null);
      setVoicePreviewUrl(null);
      setSecurityPin("");
      setPreview(null);
      setConsent(false);
      fetchEnrolledSubjects();
    } catch (error) {
      setMessage({
        text: error instanceof Error ? error.message : "Enrollment failed",
        type: "error",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteSubject(id: string) {
    if (!confirm(`Are you sure you want to deactivate subject "${id}"?`)) return;
    try {
      const res = await fetch(`${apiBase}/enrollment/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setMessage({ text: `Subject "${id}" deactivated.`, type: "info" });
        fetchEnrolledSubjects();
      } else {
        setMessage({ text: `Failed to deactivate "${id}".`, type: "error" });
      }
    } catch {
      setMessage({ text: "Error communicating with server.", type: "error" });
    }
  }

  return (
    <div className="relative">
      {/* Background Gradient Orbs */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-primary/15 rounded-full blur-[128px] animate-float" />
        <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-accent/15 rounded-full blur-[128px] animate-float-delayed" />
      </div>

      <div className="space-y-8 max-w-6xl mx-auto">
        {/* Hero Header */}
        <div className="glass-card p-8 text-center hover-lift">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 backdrop-blur-xl">
              <UserPlus className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-gray-100 to-gray-300 bg-clip-text text-transparent">
              Biometric Enrollment
            </h1>
          </div>
          <p className="text-sm text-gray-400 max-w-2xl mx-auto">
            Register reference identity templates using face detection and recognition pipeline with optional voice biometrics and security PIN
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Registration Form */}
          <div className="glass-card p-6 space-y-6">
            <div className="glass-card p-4 bg-yellow-500/5 border-yellow-500/20 flex gap-3">
              <ShieldAlert className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-gray-300">
                <span className="font-semibold">Consent Requirement:</span> Enrollment extracts a 512-d normalized mathematical vector. Original media is processed transiently and discarded.
              </div>
            </div>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Subject Identifier</label>
                <input
                  value={subjectId}
                  onChange={(e) => setSubjectId(e.target.value)}
                  placeholder="e.g. subj_1001 or username"
                  className="glass-input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">Face Capture Method</label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => {
                      if (useCamera) stopCamera();
                      setUseCamera(false);
                    }}
                    className={`btn-secondary ${!useCamera ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    <Upload className="w-4 h-4" /> Upload
                  </button>
                  <button
                    type="button"
                    onClick={startCamera}
                    className={`btn-secondary ${useCamera ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    <Camera className="w-4 h-4" /> Camera
                  </button>
                </div>

                {useCamera ? (
                  <div className="space-y-3">
                    <div className="relative aspect-video rounded-2xl overflow-hidden bg-black/50 backdrop-blur-xl border border-white/10 shadow-2xl">
                      <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                      <div className="absolute inset-0 border-2 border-primary/30 rounded-2xl pointer-events-none" />
                    </div>
                    {cameraActive && (
                      <button
                        type="button"
                        onClick={capturePhoto}
                        className="btn-primary w-full"
                      >
                        <Camera className="w-4 h-4" /> Capture Photo
                      </button>
                    )}
                  </div>
                ) : (
                  <FileDropZone
                    accept="image/jpeg,image/png,image/webp"
                    onFileSelect={(file) => {
                      setFaceImage(file);
                      setPreview(URL.createObjectURL(file));
                    }}
                    currentFile={faceImage}
                  />
                )}

                {preview && (
                  <div className="glass-card p-2 hover-lift mt-3">
                    <img src={preview} alt="Face preview" className="w-full rounded-xl object-contain max-h-56" />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Voice Biometric Sample <span className="text-xs text-gray-500">(Optional)</span>
                </label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => {
                      if (isRecording) stopVoiceRecording();
                      setUseVoiceRecorder(false);
                    }}
                    className={`btn-secondary ${!useVoiceRecorder ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    <Upload className="w-4 h-4" /> Upload
                  </button>
                  <button
                    type="button"
                    onClick={() => setUseVoiceRecorder(true)}
                    className={`btn-secondary ${useVoiceRecorder ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    <Mic className="w-4 h-4" /> Record
                  </button>
                </div>

                {useVoiceRecorder ? (
                  <div className="glass-card p-6">
                    <div className="flex flex-col items-center justify-center space-y-4">
                      {isRecording ? (
                        <>
                          <div className="relative w-full max-w-md">
                            <VoiceWave isRecording={isRecording} className="h-40" />
                            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-red-500/30 to-pink-500/30 backdrop-blur-xl flex items-center justify-center border border-red-500/40 animate-pulse">
                                <Mic className="w-10 h-10 text-red-400" />
                              </div>
                            </div>
                          </div>
                          <div className="text-3xl font-mono font-bold text-red-400">{formatDuration(recordingDuration)}</div>
                          <p className="text-xs text-gray-400">Recording... Speak clearly</p>
                          <button
                            type="button"
                            onClick={stopVoiceRecording}
                            className="btn-secondary bg-red-500/10 border-red-500/30 hover:bg-red-500/20 text-red-400"
                          >
                            <Square className="w-4 h-4" /> Stop Recording
                          </button>
                        </>
                      ) : voiceSample && voicePreviewUrl ? (
                        <>
                          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-xl flex items-center justify-center border border-emerald-500/30">
                            <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                          </div>
                          <p className="text-sm font-semibold text-emerald-400">Voice Sample Recorded</p>
                          <div className="text-xs text-gray-400 font-mono">{formatDuration(recordingDuration)}</div>
                          <audio controls src={voicePreviewUrl} className="w-full" />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={clearVoiceRecording}
                              className="btn-secondary"
                            >
                              <Trash2 className="w-4 h-4" /> Discard
                            </button>
                            <button
                              type="button"
                              onClick={() => { clearVoiceRecording(); startVoiceRecording(); }}
                              className="btn-secondary"
                            >
                              <RefreshCw className="w-4 h-4" /> Re-record
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="w-24 h-24 rounded-full glass flex items-center justify-center border-2 border-dashed border-white/20">
                            <Mic className="w-12 h-12 text-gray-400" />
                          </div>
                          <p className="text-xs text-gray-400">Click below to start recording</p>
                          <button
                            type="button"
                            onClick={startVoiceRecording}
                            className="btn-primary"
                          >
                            <Mic className="w-4 h-4" /> Start Recording
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
                    }}
                    currentFile={voiceSample}
                  />
                )}
                <p className="text-xs text-gray-500 mt-2">Used for speaker verification and synthetic speech detection.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Security PIN <span className="text-xs text-gray-500">(Optional / Recommended)</span>
                </label>
                <input
                  type="password"
                  value={securityPin}
                  onChange={(e) => setSecurityPin(e.target.value)}
                  placeholder="e.g. 482910 or custom passcode"
                  className="glass-input w-full"
                />
                <p className="text-xs text-gray-500 mt-2">Final knowledge factor for zero-trust authentication.</p>
              </div>

              <div className="flex items-start gap-3 pt-2">
                <input
                  type="checkbox"
                  id="consent"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-1 rounded border-white/20 bg-white/5 text-primary focus:ring-primary focus:ring-offset-0 focus:ring-offset-dark cursor-pointer"
                />
                <label htmlFor="consent" className="text-xs text-gray-300 cursor-pointer leading-relaxed">
                  I confirm explicit informed consent has been obtained for this reference subject.
                </label>
              </div>
            </div>

            <button
              disabled={!consent || !subjectId.trim() || !faceImage || submitting}
              onClick={submitEnrollment}
              className="btn-primary w-full !py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <UserPlus className="w-5 h-5" />
              {submitting ? "Extracting & Registering..." : "Enroll Subject Reference"}
            </button>

            {message && (
              <div
                className={`glass-card p-4 flex items-start gap-3 ${
                  message.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : message.type === "error"
                    ? "bg-red-500/10 border-red-500/30"
                    : "bg-blue-500/10 border-blue-500/30"
                }`}
              >
                {message.type === "success" ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                )}
                <span className={`text-sm ${
                  message.type === "success" ? "text-emerald-400" : message.type === "error" ? "text-red-400" : "text-blue-400"
                }`}>{message.text}</span>
              </div>
            )}
          </div>

          {/* Gallery / Enrolled Subjects List */}
          <div className="glass-card p-6 space-y-5">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Users className="w-5 h-5 text-primary" />
                  <h2 className="text-base font-semibold text-white">Enrolled Gallery</h2>
                </div>
                <p className="text-xs text-gray-400">Active identity templates in vector index</p>
              </div>
              <button
                onClick={fetchEnrolledSubjects}
                disabled={loadingSubjects}
                title="Refresh List"
                className="p-2 rounded-xl glass hover:bg-white/5 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 text-gray-400 ${loadingSubjects ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="space-y-3 max-h-[560px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
              {enrolledSubjects.length === 0 ? (
                <div className="py-24 text-center space-y-4">
                  <div className="relative inline-block">
                    <div className="w-20 h-20 rounded-full glass flex items-center justify-center border-2 border-dashed border-white/20">
                      <Users className="w-10 h-10 text-gray-400" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-gray-300 font-medium">
                      {loadingSubjects ? "Loading gallery..." : "No Subjects Enrolled"}
                    </p>
                    <p className="text-xs text-gray-500 max-w-xs mx-auto">
                      Complete the enrollment form to register your first biometric reference.
                    </p>
                  </div>
                </div>
              ) : (
                enrolledSubjects.map((item) => (
                  <div
                    key={item.subject_id}
                    className="glass-card p-4 hover-lift group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="font-semibold text-white flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse" />
                          {item.subject_id}
                        </div>
                        <div className="text-xs text-gray-400">
                          Enrolled: {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Active"}
                        </div>
                      </div>
                      <button
                        onClick={() => deleteSubject(item.subject_id)}
                        className="p-2 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                        title="Deactivate Subject"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
