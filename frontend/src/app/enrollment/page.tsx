"use client";

import { useState } from "react";
import { UserPlus, ShieldAlert } from "lucide-react";

export default function EnrollmentPage() {
  const [consent, setConsent] = useState(false);

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Subject Enrollment</h1>
        <p className="text-sm text-tf-text-muted">Register a new pseudonymous identity into the research test gallery.</p>
      </div>

      <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6">
        <div className="bg-tf-surface-muted p-4 rounded-input border border-tf-border flex gap-3 text-sm text-tf-text">
          <ShieldAlert className="w-5 h-5 text-tf-warning flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Consent Requirement:</span> Enrollment requires explicit consent under institutional research protocols. Raw media will not be permanently stored.
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-tf-text">Pseudonymous Subject ID</label>
            <input
              type="text"
              placeholder="e.g. subj_1001"
              className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-tf-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-tf-text">Reference Face Image</label>
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-sm text-tf-text-muted file:mr-4 file:py-2 file:px-4 file:rounded-input file:border file:border-tf-border file:text-xs file:font-semibold file:bg-tf-surface-muted hover:file:bg-tf-border"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-tf-text">Reference Audio Sample (16kHz WAV)</label>
            <input
              type="file"
              accept="audio/*"
              className="mt-1 block w-full text-sm text-tf-text-muted file:mr-4 file:py-2 file:px-4 file:rounded-input file:border file:border-tf-border file:text-xs file:font-semibold file:bg-tf-surface-muted hover:file:bg-tf-border"
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="consent"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="rounded border-tf-border text-tf-primary focus:ring-tf-primary"
            />
            <label htmlFor="consent" className="text-sm text-tf-text">
              I confirm informed consent for this research subject
            </label>
          </div>
        </div>

        <button
          disabled={!consent}
          className="w-full py-2.5 px-4 bg-tf-primary disabled:bg-tf-surface-muted disabled:text-tf-text-muted text-white rounded-input text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          <UserPlus className="w-4 h-4" />
          Enroll Subject Reference
        </button>
      </div>
    </div>
  );
}

