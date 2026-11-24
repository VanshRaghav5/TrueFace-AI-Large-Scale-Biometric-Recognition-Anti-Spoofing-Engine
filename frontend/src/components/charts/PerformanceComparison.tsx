"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const performanceData = [
  { metric: "EER", faceOnly: 2.8, voiceOnly: 4.5, multimodal: 1.2 },
  { metric: "APCER", faceOnly: 3.1, voiceOnly: 5.2, multimodal: 1.5 },
  { metric: "BPCER", faceOnly: 2.5, voiceOnly: 3.8, multimodal: 0.9 },
];

export default function PerformanceComparison({ className = "" }: { className?: string }) {
  return (
    <div className={`panel p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400">
          Error Rate Comparison
        </h3>
        <p className="text-xs text-gray-600 font-mono mt-1">
          Lower is better (percentage)
        </p>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={performanceData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis
            dataKey="metric"
            stroke="#666"
            style={{ fontSize: 11, fontFamily: 'monospace' }}
          />
          <YAxis
            stroke="#666"
            style={{ fontSize: 11, fontFamily: 'monospace' }}
            label={{ value: 'Error Rate (%)', angle: -90, position: 'insideLeft', fill: '#666', style: { fontSize: 10 } }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a1a',
              border: '1px solid #2a2a2a',
              borderRadius: 0,
              fontFamily: 'monospace',
              fontSize: 11,
            }}
          />
          <Legend
            wrapperStyle={{
              fontFamily: 'monospace',
              fontSize: 11,
            }}
          />
          <Bar dataKey="faceOnly" fill="#666" name="Face Only" />
          <Bar dataKey="voiceOnly" fill="#999" name="Voice Only" />
          <Bar dataKey="multimodal" fill="#10b981" name="Multimodal" />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-xs text-gray-600 font-mono">EER</div>
          <div className="text-sm text-tf-accent font-mono telemetry">1.2%</div>
        </div>
        <div>
          <div className="text-xs text-gray-600 font-mono">APCER</div>
          <div className="text-sm text-tf-accent font-mono telemetry">1.5%</div>
        </div>
        <div>
          <div className="text-xs text-gray-600 font-mono">BPCER</div>
          <div className="text-sm text-tf-accent font-mono telemetry">0.9%</div>
        </div>
      </div>
    </div>
  );
}
