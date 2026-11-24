"use client";

interface CircularGaugeProps {
  value: number; // 0-100
  label: string;
  unit?: string;
  max?: number;
  thresholds?: { warning: number; critical: number };
}

export default function CircularGauge({
  value,
  label,
  unit = "%",
  max = 100,
  thresholds = { warning: 70, critical: 90 },
}: CircularGaugeProps) {
  const percentage = Math.min(100, (value / max) * 100);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const offset = circumference - (percentage / 100) * circumference;

  const getColor = () => {
    if (value >= thresholds.critical) return "#f97316"; // orange
    if (value >= thresholds.warning) return "#fbbf24"; // yellow
    return "#10b981"; // emerald
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg className="transform -rotate-90 w-32 h-32">
          {/* Background circle */}
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke="#2a2a2a"
            strokeWidth="8"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke={getColor()}
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold font-mono text-white tabular-nums">
            {value.toFixed(0)}
          </span>
          <span className="text-xs text-gray-500 font-mono">{unit}</span>
        </div>
      </div>
      <span className="text-xs font-mono text-gray-400 uppercase tracking-wider mt-2">
        {label}
      </span>
    </div>
  );
}
