import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score?: number): string {
  if (score === undefined || score === null) return "N/A";
  return (score * 100).toFixed(1) + "%";
}

