"use client";

import { useState } from "react";
import { UserPlus, ShieldAlert } from "lucide-react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function EnrollmentPage() {
  const [consent, setConsent] = useState(false);
  const [subjectId, setSubjectId] = useState("");
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submitEnrollment() {
    if (!subjectId || !faceImage || !consent) return;
    setSubmitting(true);
    setMessage("");
    const form = new FormData();
    form.append("subject_id", subjectId);
    form.append("consent_confirmed", "true");
    form.append("face_image", faceImage);
    try {
      const response = await fetch(`${apiBase}/enrollment`, { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Enrollment failed");
      setMessage(`${payload.status}: ${payload.detail ?? "Enrollment persisted"}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Enrollment failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Subject Enrollment</h1>
        <p className="text-sm text-tf-text-muted">Enroll a consented face template using the configured ArcFace runtime.</p>
      </div>
      <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6">
        <div className="bg-tf-surface-muted p-4 rounded-input border border-tf-border flex gap-3 text-sm text-tf-text">
          <ShieldAlert className="w-5 h-5 text-tf-warning flex-shrink-0 mt-0.5" />
          <div><span className="font-semibold">Consent Requirement:</span> Enrollment requires explicit consent. Raw media is processed transiently and is not stored.</div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-tf-text">Pseudonymous Subject ID</label>
            <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} placeholder="e.g. subj_1001" className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-tf-text">Reference Face Image</label>
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              setFaceImage(file);
              setPreview(file ? URL.createObjectURL(file) : null);
            }} className="mt-1 block w-full text-sm text-tf-text-muted" />
          </div>
          {preview && <img src={preview} alt="Selected face preview" className="max-h-64 rounded-input object-contain" />}
          <div className="flex items-center gap-2 pt-2">
            <input type="checkbox" id="consent" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <label htmlFor="consent" className="text-sm text-tf-text">I confirm informed consent for this research subject</label>
          </div>
        </div>
        <button disabled={!consent || !subjectId || !faceImage || submitting} onClick={submitEnrollment} className="w-full py-2.5 px-4 bg-tf-primary disabled:bg-tf-surface-muted disabled:text-tf-text-muted text-white rounded-input text-sm font-medium flex items-center justify-center gap-2">
          <UserPlus className="w-4 h-4" /> {submitting ? "Processing..." : "Enroll Subject Reference"}
        </button>
        {message && <p className="text-sm text-tf-text-muted" role="status">{message}</p>}
      </div>
    </div>
  );
}
