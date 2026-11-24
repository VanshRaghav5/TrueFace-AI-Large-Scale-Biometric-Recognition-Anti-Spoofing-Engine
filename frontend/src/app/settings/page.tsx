"use client";

import { useState } from "react";
import { Save, Settings as SettingsIcon, TrendingUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";

// Generate distribution curve data
const generateDistributionData = (threshold: number) => {
  const data = [];
  for (let x = 0; x <= 1; x += 0.01) {
    const genuine = Math.exp(-Math.pow(x - 0.85, 2) / 0.02); // Peak at 0.85
    const impostor = Math.exp(-Math.pow(x - 0.3, 2) / 0.03); // Peak at 0.3
    data.push({ score: x, genuine, impostor, threshold: x === threshold ? 1.5 : null });
  }
  return data;
};

export default function SettingsPage() {
  const [faceThreshold, setFaceThreshold] = useState(0.75);
  const [voiceThreshold, setVoiceThreshold] = useState(0.70);
  const [padThreshold, setPadThreshold] = useState(0.80);
  const [deepfakeThreshold, setDeepfakeThreshold] = useState(0.70);

  const distributionData = generateDistributionData(faceThreshold);

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="panel p-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-tf-surface border border-tf-border flex items-center justify-center">
            <SettingsIcon className="w-6 h-6 text-tf-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">SYSTEM CONFIGURATION</h1>
            <p className="text-xs text-gray-500 font-mono mt-1">DECISION POLICY THRESHOLDS AND CALIBRATION</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Threshold Controls */}
        <div className="panel p-6 space-y-6">
          <div>
            <h2 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-6 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-tf-accent" /> Acceptance Thresholds
            </h2>
            
            <div className="space-y-6">
              {/* Face Match */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-mono text-gray-300">Face Match (Cosine)</label>
                  <span className="text-sm font-mono text-tf-accent tabular-nums">
                    {faceThreshold.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={faceThreshold}
                  onChange={(e) => setFaceThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-tf-surface border border-tf-border appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-tf-accent [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-tf-bg [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-tf-accent [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-tf-bg [&::-moz-range-thumb]:rounded-none"
                />
                <div className="flex justify-between text-xs text-gray-600 font-mono mt-1">
                  <span>0.00</span>
                  <span>0.50</span>
                  <span>1.00</span>
                </div>
              </div>

              {/* Voice Match */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-mono text-gray-300">Voice Match (Cosine)</label>
                  <span className="text-sm font-mono text-tf-accent tabular-nums">
                    {voiceThreshold.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={voiceThreshold}
                  onChange={(e) => setVoiceThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-tf-surface border border-tf-border appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-tf-accent [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-tf-bg [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-tf-accent [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-tf-bg [&::-moz-range-thumb]:rounded-none"
                />
                <div className="flex justify-between text-xs text-gray-600 font-mono mt-1">
                  <span>0.00</span>
                  <span>0.50</span>
                  <span>1.00</span>
                </div>
              </div>

              {/* PAD */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-mono text-gray-300">PAD Genuineness</label>
                  <span className="text-sm font-mono text-tf-accent tabular-nums">
                    {padThreshold.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={padThreshold}
                  onChange={(e) => setPadThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-tf-surface border border-tf-border appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-tf-accent [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-tf-bg [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-tf-accent [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-tf-bg [&::-moz-range-thumb]:rounded-none"
                />
                <div className="flex justify-between text-xs text-gray-600 font-mono mt-1">
                  <span>0.00</span>
                  <span>0.50</span>
                  <span>1.00</span>
                </div>
              </div>

              {/* Deepfake */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-mono text-gray-300">Deepfake Authenticity</label>
                  <span className="text-sm font-mono text-tf-accent tabular-nums">
                    {deepfakeThreshold.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={deepfakeThreshold}
                  onChange={(e) => setDeepfakeThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-tf-surface border border-tf-border appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-tf-accent [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-tf-bg [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-tf-accent [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-tf-bg [&::-moz-range-thumb]:rounded-none"
                />
                <div className="flex justify-between text-xs text-gray-600 font-mono mt-1">
                  <span>0.00</span>
                  <span>0.50</span>
                  <span>1.00</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-tf-border">
            <button className="btn-primary w-full">
              <Save className="w-4 h-4" />
              Save Configuration
            </button>
          </div>
        </div>

        {/* Score Distribution Visualization */}
        <div className="panel p-6">
          <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">
            Score Distribution (Genuine vs Impostor)
          </h3>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={distributionData}>
              <defs>
                <linearGradient id="genuineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="impostorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f97316" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis
                dataKey="score"
                stroke="#6b7280"
                style={{ fontSize: "11px", fontFamily: "monospace" }}
                tickFormatter={(value) => value.toFixed(1)}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: "11px", fontFamily: "monospace" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "2px",
                  fontSize: "12px",
                  fontFamily: "monospace",
                }}
                formatter={(value: any) => value?.toFixed(2)}
              />
              <Area
                type="monotone"
                dataKey="genuine"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#genuineGradient)"
                name="Genuine"
              />
              <Area
                type="monotone"
                dataKey="impostor"
                stroke="#f97316"
                strokeWidth={2}
                fill="url(#impostorGradient)"
                name="Impostor"
              />
              <Line
                type="monotone"
                dataKey="threshold"
                stroke="#ffffff"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
                name="Threshold"
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="mt-4 flex items-center justify-center gap-6 text-xs font-mono">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-tf-accent" />
              <span className="text-gray-400">Genuine</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-tf-alert" />
              <span className="text-gray-400">Impostor</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 bg-white" />
              <span className="text-gray-400">Threshold</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

