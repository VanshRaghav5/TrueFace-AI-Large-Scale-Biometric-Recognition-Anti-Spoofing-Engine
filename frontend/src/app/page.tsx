import Link from "next/link";
import { ShieldCheck, UserCheck, Activity, FileText } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-8 py-6">
      <div className="border border-tf-border rounded-card bg-tf-surface p-8 shadow-sm">
        <h1 className="text-3xl font-bold tracking-tight text-tf-text">
          TrueFace AI-X Prototype
        </h1>
        <p className="mt-2 text-base text-tf-text-muted max-w-2xl">
          Multimodal Biometric Recognition, Deepfake Detection &amp; Anti-Spoofing Engine.
          Evaluating the fusion of face and voice identity with independent authenticity and liveness verification.
        </p>
        <div className="mt-6 flex flex-wrap gap-4">
          <Link
            href="/authentication"
            className="px-4 py-2.5 bg-tf-primary hover:bg-tf-primary-hover text-white rounded-input font-medium text-sm transition-colors"
          >
            Run Authentication Test
          </Link>
          <Link
            href="/enrollment"
            className="px-4 py-2.5 bg-tf-surface-muted hover:bg-tf-border text-tf-text rounded-input font-medium text-sm border border-tf-border transition-colors"
          >
            Enroll New Subject
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Link href="/authentication" className="border border-tf-border rounded-card bg-tf-surface p-6 hover:border-tf-primary transition-colors">
          <ShieldCheck className="w-8 h-8 text-tf-primary mb-3" />
          <h2 className="text-lg font-semibold text-tf-text">Authentication</h2>
          <p className="mt-1 text-sm text-tf-text-muted">
            Test 1:1 and 1:N verification with face PAD, deepfake, and audio anti-spoofing checks.
          </p>
        </Link>

        <Link href="/enrollment" className="border border-tf-border rounded-card bg-tf-surface p-6 hover:border-tf-primary transition-colors">
          <UserCheck className="w-8 h-8 text-tf-primary mb-3" />
          <h2 className="text-lg font-semibold text-tf-text">Consent Enrollment</h2>
          <p className="mt-1 text-sm text-tf-text-muted">
            Register test identities with explicit consent verification into the controlled gallery.
          </p>
        </Link>

        <Link href="/audit" className="border border-tf-border rounded-card bg-tf-surface p-6 hover:border-tf-primary transition-colors">
          <FileText className="w-8 h-8 text-tf-primary mb-3" />
          <h2 className="text-lg font-semibold text-tf-text">Audit Log Review</h2>
          <p className="mt-1 text-sm text-tf-text-muted">
            Inspect verification attempts, reason codes, confidence intervals, and decision forensics.
          </p>
        </Link>

        <Link href="/evaluation" className="border border-tf-border rounded-card bg-tf-surface p-6 hover:border-tf-primary transition-colors">
          <Activity className="w-8 h-8 text-tf-primary mb-3" />
          <h2 className="text-lg font-semibold text-tf-text">Evaluation Suite</h2>
          <p className="mt-1 text-sm text-tf-text-muted">
            Compare face-only, voice-only, and fused performance metrics across test benchmarks.
          </p>
        </Link>
      </div>
    </div>
  );
}

