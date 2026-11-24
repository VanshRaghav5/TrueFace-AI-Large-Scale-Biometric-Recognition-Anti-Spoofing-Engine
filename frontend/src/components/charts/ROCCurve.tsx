"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface ROCCurveProps {
  className?: string;
}

// Mock data - replace with real benchmark data
const mockROCData = Array.from({ length: 50 }, (_, i) => {
  const fpr = i / 50;
  return {
    fpr: fpr.toFixed(3),
    faceOnly: Math.min(1, fpr + 0.1 + Math.random() * 0.1),
    voiceOnly: Math.min(1, fpr + 0.15 + Math.random() * 0.1),
    multimodal: Math.min(1, fpr + 0.05 + Math.random() * 0.08),
  };
});

export default function ROCCurve({ className = "" }: ROCCurveProps) {
  return (
    <div className={`panel p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400">
          ROC Curve Analysis
        </h3>
        <p className="text-xs text-gray-600 font-mono mt-1">
          True Positive Rate vs False Positive Rate
        </p>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={mockROCData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis
            dataKey="fpr"
            stroke="#666"
            style={{ fontSize: 11, fontFamily: 'monospace' }}
            label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5, fill: '#666', style: { fontSize: 10 } }}
          />
          <YAxis
            stroke="#666"
            style={{ fontSize: 11, fontFamily: 'monospace' }}
            label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', fill: '#666', style: { fontSize: 10 } }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a1a',
              border: '1px solid #2a2a2a',
              borderRadius: 0,
              fontFamily: 'monospace',
              fontSize: 11,
            }}
            labelStyle={{ color: '#10b981' }}
          />
          <Legend
            wrapperStyle={{
              fontFamily: 'monospace',
              fontSize: 11,
            }}
          />
          <Line
            type="monotone"
            dataKey="multimodal"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            name="Multimodal Fusion"
          />
          <Line
            type="monotone"
            dataKey="faceOnly"
            stroke="#666"
            strokeWidth={1.5}
            dot={false}
            name="Face Only"
            strokeDasharray="5 5"
          />
          <Line
            type="monotone"
            dataKey="voiceOnly"
            stroke="#999"
            strokeWidth={1.5}
            dot={false}
            name="Voice Only"
            strokeDasharray="3 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
