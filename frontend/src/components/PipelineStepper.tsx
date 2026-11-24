"use client";

import { Check, Loader2, X } from "lucide-react";

export interface PipelineStep {
  id: number;
  name: string;
  status: "pending" | "processing" | "success" | "failed";
}

interface PipelineStepperProps {
  steps: PipelineStep[];
  className?: string;
}

export default function PipelineStepper({ steps, className = "" }: PipelineStepperProps) {
  return (
    <div className={`panel p-6 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step indicator */}
            <div className="flex flex-col items-center flex-1">
              <div
                className={`
                  w-8 h-8 border flex items-center justify-center transition-all
                  ${step.status === "success"
                    ? "border-tf-accent bg-tf-accent/10 text-tf-accent"
                    : step.status === "failed"
                    ? "border-tf-alert bg-tf-alert/10 text-tf-alert"
                    : step.status === "processing"
                    ? "border-tf-accent animate-pulse text-tf-accent"
                    : "border-tf-border text-gray-700"
                  }
                `}
              >
                {step.status === "success" ? (
                  <Check className="w-4 h-4" />
                ) : step.status === "failed" ? (
                  <X className="w-4 h-4" />
                ) : step.status === "processing" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span className="text-xs font-mono">{step.id}</span>
                )}
              </div>
              <div className="mt-2 text-center">
                <div
                  className={`
                    text-xs font-mono uppercase tracking-wider
                    ${step.status === "success"
                      ? "text-tf-accent"
                      : step.status === "failed"
                      ? "text-tf-alert"
                      : step.status === "processing"
                      ? "text-tf-accent"
                      : "text-gray-600"
                    }
                  `}
                >
                  {step.name}
                </div>
              </div>
            </div>

            {/* Connector line */}
            {index < steps.length - 1 && (
              <div
                className={`
                  h-px flex-1 transition-all mx-2 mt-[-20px]
                  ${step.status === "success"
                    ? "bg-tf-accent"
                    : step.status === "processing"
                    ? "bg-tf-accent/50"
                    : "bg-tf-border"
                  }
                `}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
