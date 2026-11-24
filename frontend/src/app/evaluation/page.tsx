"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import ROCCurve from "@/components/charts/ROCCurve";
import PerformanceComparison from "@/components/charts/PerformanceComparison";

export default function EvaluationPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [hasResults, setHasResults] = useState(false);

  const runBenchmark = async () => {
    setIsRunning(true);
    setProgress(0);
    
    // Simulate benchmark run
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 300));
      setProgress(i);
    }
    
    setIsRunning(false);
    setHasResults(true);
  };

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">MODEL EVALUATION SUITE</h1>
            <p className="text-xs text-gray-500 font-mono mt-1">
              Benchmark comparison across Face-only, Voice-only, and Multimodal Fused pipelines
            </p>
          </div>
          <button 
            onClick={runBenchmark}
            disabled={isRunning}
            className="btn-primary disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Benchmark
              </>
            )}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      {isRunning && (
        <div className="panel p-4">
          <div className="h-1 bg-tf-border">
            <div 
              className="h-full bg-tf-accent transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2 font-mono">
            Processing benchmark: {progress}% complete
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="panel p-6">
          <h2 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">
            Face-Only Baseline
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">EER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "2.8%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">APCER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "3.1%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">BPCER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "2.5%" : "—"}
              </span>
            </div>
          </div>
        </div>

        <div className="panel p-6">
          <h2 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">
            Voice-Only Baseline
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">EER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "4.5%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">APCER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "5.2%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">BPCER:</span>
              <span className="font-mono telemetry text-white">
                {hasResults ? "3.8%" : "—"}
              </span>
            </div>
          </div>
        </div>

        <div className="panel p-6 border-tf-accent">
          <h2 className="text-sm font-mono uppercase tracking-wider text-tf-accent mb-4">
            Multimodal Fused
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">EER:</span>
              <span className="font-mono telemetry text-tf-accent">
                {hasResults ? "1.2%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">APCER:</span>
              <span className="font-mono telemetry text-tf-accent">
                {hasResults ? "1.5%" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-mono">BPCER:</span>
              <span className="font-mono telemetry text-tf-accent">
                {hasResults ? "0.9%" : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      {hasResults ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ROCCurve />
          <PerformanceComparison />
        </div>
      ) : (
        <div className="panel p-12 text-center">
          <Play className="w-12 h-12 mx-auto mb-4 text-gray-700" />
          <p className="text-sm text-gray-500 font-mono">
            Click "Run Benchmark" to generate performance charts
          </p>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-gray-600 font-mono">
        © {new Date().getFullYear()} TrueFace AI-X. All rights reserved.
      </div>
    </div>
  );
}
