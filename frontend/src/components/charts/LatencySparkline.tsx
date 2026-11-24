"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useMemo } from "react";

interface LatencySparklineProps {
  dataPoints?: number[];
  className?: string;
}

export default function LatencySparkline({ dataPoints, className = "" }: LatencySparklineProps) {
  // Mock real-time latency data
  const data = useMemo(() => {
    const points = dataPoints || Array.from({ length: 30 }, () => 
      Math.floor(Math.random() * 30) + 15 // 15-45ms range
    );
    return points.map((value, index) => ({ index, value }));
  }, [dataPoints]);

  const avg = useMemo(() => {
    const sum = data.reduce((acc, d) => acc + d.value, 0);
    return (sum / data.length).toFixed(0);
  }, [data]);

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex-1 h-12">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <Line
              type="monotone"
              dataKey="value"
              stroke="#10b981"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-right">
        <div className="text-lg font-mono font-bold text-tf-accent telemetry">{avg}ms</div>
        <div className="text-xs text-gray-600 font-mono">avg</div>
      </div>
    </div>
  );
}
