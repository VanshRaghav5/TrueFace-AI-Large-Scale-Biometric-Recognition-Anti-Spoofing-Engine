export default function EvaluationPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Model Evaluation Suite</h1>
        <p className="text-sm text-tf-text-muted">
          Benchmark comparison across Face-only, Voice-only, and Multimodal Fused pipelines.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Face-Only Baseline</h2>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-tf-text-muted">EER:</span>
              <span className="font-mono font-medium">Pending test run</span>
            </div>
            <div className="flex justify-between">
              <span className="text-tf-text-muted">APCER @ BPCER=1%:</span>
              <span className="font-mono font-medium">Pending test run</span>
            </div>
          </div>
        </div>

        <div className="border border-tf-border rounded-card bg-tf-surface p-5">
          <h2 className="text-sm font-semibold text-tf-text-muted">Voice-Only Baseline</h2>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-tf-text-muted">EER:</span>
              <span className="font-mono font-medium">Pending test run</span>
            </div>
            <div className="flex justify-between">
              <span className="text-tf-text-muted">Anti-spoof EER:</span>
              <span className="font-mono font-medium">Pending test run</span>
            </div>
          </div>
        </div>

        <div className="border border-tf-border rounded-card bg-tf-surface p-5 border-l-4 border-l-tf-primary">
          <h2 className="text-sm font-semibold text-tf-primary">Multimodal Fused Engine</h2>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-tf-text-muted">Target EER:</span>
              <span className="font-mono font-medium">&lt; Face Baseline</span>
            </div>
            <div className="flex justify-between">
              <span className="text-tf-text-muted">FAR @ FRR=0.1%:</span>
              <span className="font-mono font-medium">Pending test run</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

