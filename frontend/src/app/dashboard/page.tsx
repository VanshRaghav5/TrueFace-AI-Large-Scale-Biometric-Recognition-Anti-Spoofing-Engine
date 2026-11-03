export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">System Dashboard</h1>
        <p className="text-sm text-tf-text-muted">Real-time status of pipeline branches, vector store, and risk engine.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Face Pipeline Status</h2>
          <div className="mt-2 text-2xl font-bold text-tf-success">Ready</div>
          <p className="mt-1 text-xs text-tf-text-muted">RetinaFace + ArcFace + MiniFASNet</p>
        </div>
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Voice Pipeline Status</h2>
          <div className="mt-2 text-2xl font-bold text-tf-success">Ready</div>
          <p className="mt-1 text-xs text-tf-text-muted">Silero VAD + ECAPA-TDNN + AASIST</p>
        </div>
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Vector Store (FAISS)</h2>
          <div className="mt-2 text-2xl font-bold text-tf-text">Active</div>
          <p className="mt-1 text-xs text-tf-text-muted">Controlled Gallery Index</p>
        </div>
      </div>
    </div>
  );
}

