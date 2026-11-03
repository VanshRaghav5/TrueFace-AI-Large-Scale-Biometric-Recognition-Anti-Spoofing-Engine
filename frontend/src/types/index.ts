export type Decision = "allow" | "step_up" | "block" | "error";

export type ReasonCode =
  | "FACE_IDENTITY_MATCH"
  | "FACE_IDENTITY_MISMATCH"
  | "FACE_QUALITY_LOW"
  | "FACE_PAD_RISK"
  | "FACE_MANIPULATION_RISK"
  | "VOICE_IDENTITY_MATCH"
  | "VOICE_IDENTITY_MISMATCH"
  | "AUDIO_QUALITY_LOW"
  | "AUDIO_SPOOF_RISK"
  | "MODALITY_MISSING"
  | "MODEL_TIMEOUT"
  | "MODEL_UNAVAILABLE"
  | "SIGNAL_CONFLICT";

export interface FaceResult {
  status: "available" | "missing" | "invalid" | "low_quality" | "unsupported" | "timeout" | "model_unavailable" | "error";
  identity_score?: number;
  liveness_score?: number;
  deepfake_score?: number;
  quality_score?: number;
}

export interface VoiceResult {
  status: "available" | "missing" | "invalid" | "low_quality" | "unsupported" | "timeout" | "model_unavailable" | "error";
  identity_score?: number;
  antispoof_score?: number;
  quality_score?: number;
}

export interface VerificationResponse {
  session_id: string;
  claimed_subject_id?: string;
  overall_decision: Decision;
  fused_authenticity_score: number;
  fused_identity_score: number;
  reason_codes: ReasonCode[];
  face_result: FaceResult;
  voice_result: VoiceResult;
  evaluated_at: string;
}

export interface AuditEventItem {
  id: string;
  session_id: string;
  subject_id?: string;
  overall_decision: Decision;
  reason_codes: ReasonCode[];
  fused_score?: number;
  latency_ms: number;
  created_at: string;
}

