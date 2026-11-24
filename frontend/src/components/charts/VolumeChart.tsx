"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface VolumeChartProps {
  data: Array<{ hour: string; count: number }>;
}

export default function VolumeChart({ data }: VolumeChartProps) {
  return (
    <div className="panel p-6">
      <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">
        24h Verification Volume
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis
            dataKey="hour"
            stroke="#6b7280"
            style={{ fontSize: "11px", fontFamily: "monospace" }}
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
            labelStyle={{ color: "#10b981" }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#volumeGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
