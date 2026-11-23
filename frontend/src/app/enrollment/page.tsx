"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { UserPlus, ShieldAlert, Camera, Upload, Trash2, CheckCircle2, AlertCircle, RefreshCw, Mic, MicOff, Square } from "lucide-react";

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
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Subject Enrollment</h1>
        <p className="text-sm text-tf-text-muted mt-1">
          Register a reference identity into the TrueFace AI-X gallery using the InsightFace (SCRFD + ArcFace) pipeline.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Registration Form */}
        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6 shadow-sm">
          <div className="bg-tf-surface-muted p-4 rounded-input border border-tf-border flex gap-3 text-xs text-tf-text">
            <ShieldAlert className="w-4 h-4 text-tf-warning flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Consent Requirement:</span> Enrollment extracts a 512-d normalized mathematical vector. Original media is processed transiently and discarded.
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-tf-text">Subject Identifier</label>
              <input
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                placeholder="e.g. subj_1001"
                className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:border-tf-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-tf-text mb-2">Face Capture Method</label>
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
            </div>

            {useCamera ? (
              <div className="space-y-2">
                <div className="relative aspect-video rounded-input overflow-hidden bg-black border border-tf-border">
                  <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                </div>
                {cameraActive && (
                  <button
                    type="button"
                    onClick={capturePhoto}
                    className="w-full py-2 bg-tf-success text-white rounded-input text-xs font-medium flex items-center justify-center gap-1.5"
                  >
                    <Camera className="w-3.5 h-3.5" /> Capture Photo
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
              <div className="relative rounded-input overflow-hidden border border-tf-border bg-tf-surface-muted p-1">
                <img src={preview} alt="Selected face preview" className="max-h-48 w-full rounded-input object-contain" />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-tf-text mb-2">
                Voice Biometric Sample <span className="text-xs text-tf-text-muted">(optional)</span>
              </label>
              <div className="flex gap-2 mb-2">
                <button
                  type="button"
                  onClick={() => {
                    if (isRecording) stopVoiceRecording();
                    setUseVoiceRecorder(false);
                  }}
                  className={`flex-1 py-2 px-3 rounded-input text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                    !useVoiceRecorder
                      ? "bg-tf-primary text-white border-tf-primary"
                      : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                  }`}
                >
                  <Upload className="w-3.5 h-3.5" /> Upload .wav
                </button>
                <button
                  type="button"
                  onClick={() => setUseVoiceRecorder(true)}
                  className={`flex-1 py-2 px-3 rounded-input text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                    useVoiceRecorder
                      ? "bg-tf-primary text-white border-tf-primary"
                      : "bg-tf-surface text-tf-text border-tf-border hover:bg-tf-surface-muted"
                  }`}
                >
                  <Mic className="w-3.5 h-3.5" /> Live Record
                </button>
              </div>

              {useVoiceRecorder ? (
                <div className="space-y-2">
                  <div className="relative rounded-input overflow-hidden bg-tf-surface-muted border border-tf-border p-4">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      {isRecording ? (
                        <>
                          <div className="relative">
                            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center animate-pulse">
                              <Mic className="w-8 h-8 text-red-600" />
                            </div>
                            <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 animate-ping" />
                          </div>
                          <div className="text-sm font-mono font-bold text-red-600">{formatDuration(recordingDuration)}</div>
                          <p className="text-[11px] text-tf-text-muted">Recording... Speak clearly into your microphone</p>
                          <button
                            type="button"
                            onClick={stopVoiceRecording}
                            className="py-2 px-6 bg-red-600 text-white rounded-input text-xs font-medium flex items-center gap-1.5 hover:bg-red-700 transition-colors"
                          >
                            <Square className="w-3.5 h-3.5" /> Stop Recording
                          </button>
                        </>
                      ) : voiceSample && voicePreviewUrl ? (
                        <>
                          <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
                            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                          </div>
                          <p className="text-xs font-semibold text-emerald-700">Voice Sample Recorded ({formatDuration(recordingDuration)})</p>
                          <audio controls src={voicePreviewUrl} className="w-full max-w-xs" />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={clearVoiceRecording}
                              className="py-1.5 px-4 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-xs font-medium transition-colors"
                            >
                              <Trash2 className="w-3 h-3 inline mr-1" /> Discard
                            </button>
                            <button
                              type="button"
                              onClick={() => { clearVoiceRecording(); startVoiceRecording(); }}
                              className="py-1.5 px-4 border border-tf-border text-tf-text hover:bg-tf-surface-muted rounded-input text-xs font-medium transition-colors"
                            >
                              <RefreshCw className="w-3 h-3 inline mr-1" /> Re-record
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="w-16 h-16 rounded-full bg-tf-surface flex items-center justify-center border-2 border-dashed border-tf-border">
                            <Mic className="w-8 h-8 text-tf-text-muted" />
                          </div>
                          <p className="text-xs text-tf-text-muted">Click below to start recording your voice</p>
                          <button
                            type="button"
                            onClick={startVoiceRecording}
                            className="py-2 px-6 bg-tf-primary text-white rounded-input text-xs font-medium flex items-center gap-1.5 hover:bg-tf-primary-hover transition-colors"
                          >
                            <Mic className="w-3.5 h-3.5" /> Start Recording
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  <p className="text-[11px] text-tf-text-muted">Speak for 3-10 seconds for best speaker verification accuracy. Auto-converts to WAV.</p>
                </div>
              ) : (
                <div>
                  <input
                    type="file"
                    accept="audio/wav,audio/x-wav"
                    onChange={(e) => { setVoiceSample(e.target.files?.[0] ?? null); setVoicePreviewUrl(null); }}
                    className="block w-full text-xs text-tf-text-muted file:mr-3 file:py-1.5 file:px-3 file:rounded-input file:border-0 file:text-xs file:font-medium file:bg-tf-surface-muted file:text-tf-text hover:file:bg-tf-border"
                  />
                  {voiceSample && <div className="text-[11px] text-emerald-600 font-mono mt-1">Loaded: {voiceSample.name}</div>}
                </div>
              )}
              <p className="text-[11px] text-tf-text-muted mt-0.5">Used for speaker verification and synthetic speech anti-spoofing.</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-tf-text">
                Security PIN / Final Secret Code <span className="text-xs text-tf-text-muted">(Optional / Recommended)</span>
              </label>
              <input
                type="password"
                value={securityPin}
                onChange={(e) => setSecurityPin(e.target.value)}
                placeholder="e.g. 482910 or custom passcode"
                className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:border-tf-primary"
              />
              <p className="text-[11px] text-tf-text-muted mt-0.5">Enforces final possession/knowledge factor before access is granted.</p>
            </div>

            <div className="flex items-start gap-2 pt-2">
              <input
                type="checkbox"
                id="consent"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 rounded border-tf-border text-tf-primary focus:ring-tf-primary"
              />
              <label htmlFor="consent" className="text-xs text-tf-text cursor-pointer leading-relaxed">
                I confirm explicit informed consent has been obtained for this reference subject.
              </label>
            </div>
          </div>

          <button
            disabled={!consent || !subjectId.trim() || !faceImage || submitting}
            onClick={submitEnrollment}
            className="w-full py-2.5 px-4 bg-tf-primary disabled:bg-tf-surface-muted disabled:text-tf-text-muted text-white rounded-input text-sm font-medium flex items-center justify-center gap-2 transition-colors hover:bg-tf-primary-hover shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            {submitting ? "Extracting & Registering..." : "Enroll Subject Reference"}
          </button>

          {message && (
            <div
              className={`p-3 rounded-input text-xs flex items-center gap-2 ${
                message.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : message.type === "error"
                  ? "bg-red-50 text-red-800 border border-red-200"
                  : "bg-blue-50 text-blue-800 border border-blue-200"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              )}
              <span>{message.text}</span>
            </div>
          )}
        </div>

        {/* Gallery / Enrolled Subjects List */}
        <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-4 shadow-sm flex flex-col">
          <div className="flex items-center justify-between border-b border-tf-border pb-3">
            <div>
              <h2 className="text-base font-semibold text-tf-text">Enrolled Gallery</h2>
              <p className="text-xs text-tf-text-muted">Active identity templates in the database and FAISS index</p>
            </div>
            <button
              onClick={fetchEnrolledSubjects}
              disabled={loadingSubjects}
              title="Refresh List"
              className="p-1.5 rounded-input text-tf-text-muted hover:text-tf-text hover:bg-tf-surface-muted"
            >
              <RefreshCw className={`w-4 h-4 ${loadingSubjects ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[460px] space-y-2.5">
            {enrolledSubjects.length === 0 ? (
              <div className="py-12 text-center text-xs text-tf-text-muted">
                {loadingSubjects ? "Loading gallery..." : "No subjects enrolled yet. Complete the form to enroll your first face."}
              </div>
            ) : (
              enrolledSubjects.map((item) => (
                <div
                  key={item.subject_id}
                  className="flex items-center justify-between p-3 rounded-input border border-tf-border bg-tf-surface-muted text-xs hover:border-tf-primary/50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="font-semibold text-tf-text flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                      {item.subject_id}
                    </div>
                    <div className="text-[11px] text-tf-text-muted">
                      Enrolled: {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Active"}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteSubject(item.subject_id)}
                    className="p-1.5 text-tf-text-muted hover:text-tf-danger rounded-input hover:bg-tf-surface transition-colors"
                    title="Deactivate Subject"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
