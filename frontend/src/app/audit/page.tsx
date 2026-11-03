export default function AuditPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-tf-text">Audit Log &amp; Forensics</h1>
        <p className="text-sm text-tf-text-muted">
          Tamper-evident record of verification attempts, decisions, calibrated scores, and reason codes.
        </p>
      </div>

      <div className="border border-tf-border rounded-card bg-tf-surface overflow-hidden">
        <table className="min-w-full divide-y divide-tf-border text-sm">
          <thead className="bg-tf-surface-muted text-tf-text-muted text-left text-xs uppercase font-medium">
            <tr>
              <th className="px-6 py-3">Timestamp</th>
              <th className="px-6 py-3">Session ID</th>
              <th className="px-6 py-3">Claimed Subject</th>
              <th className="px-6 py-3">Decision</th>
              <th className="px-6 py-3">Reason Codes</th>
              <th className="px-6 py-3">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-tf-border text-tf-text">
            <tr>
              <td colSpan={6} className="px-6 py-8 text-center text-tf-text-muted">
                No recent audit events recorded. Run an authentication test to generate audit logs.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

