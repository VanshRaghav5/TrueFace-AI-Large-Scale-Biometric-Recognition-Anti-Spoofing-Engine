"use client";

interface MetricDisplayProps {
  label: string;
  value: string | number;
  unit?: string;
  status?: "success" | "warning" | "error" | "neutral";
  className?: string;
}

const statusColors = {
  success: "text-emerald-400",
  warning: "text-yellow-400",
  error: "text-orange-400",
  neutral: "text-gray-300",
};

export default function MetricDisplay({
  label,
  value,
  unit = "",
  status = "neutral",
  className = "",
}: MetricDisplayProps) {
  const colorClass = statusColors[status];

  return (
    <div className={`panel p-4 ${className}`}>
      <div className="metric-label">{label}</div>
      <div className={`metric ${colorClass}`}>
        {value}
        {unit && <span className="text-sm ml-1 text-gray-600">{unit}</span>}
      </div>
    </div>
  );
}
