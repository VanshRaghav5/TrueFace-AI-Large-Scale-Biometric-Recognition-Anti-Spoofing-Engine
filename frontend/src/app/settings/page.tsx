export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">System Configuration</h1>
        <p className="text-sm text-tf-text-muted">Thresholds, calibration weights, and model endpoint preferences.</p>
      </div>

      <div className="border border-tf-border rounded-card bg-tf-surface p-6 space-y-6">
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-tf-text">Decision Policy Thresholds</h2>
          <div>
            <label className="block text-sm font-medium text-tf-text">Face Match Acceptance Threshold (Cosine)</label>
            <input
              type="number"
              defaultValue={0.75}
              step={0.01}
              className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-tf-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-tf-text">Voice Match Acceptance Threshold (Cosine)</label>
            <input
              type="number"
              defaultValue={0.70}
              step={0.01}
              className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-tf-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-tf-text">PAD Min Genuineness Confidence</label>
            <input
              type="number"
              defaultValue={0.80}
              step={0.01}
              className="mt-1 block w-full rounded-input border border-tf-border bg-tf-surface px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-tf-primary"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-tf-border">
          <button className="px-4 py-2 bg-tf-primary text-white rounded-input text-sm font-medium hover:bg-tf-primary-hover transition-colors">
            Save Threshold Configuration
          </button>
        </div>
      </div>
    </div>
  );
}

