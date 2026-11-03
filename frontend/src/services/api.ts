import { VerificationResponse } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export async function verifyBiometrics(formData: FormData): Promise<VerificationResponse> {
  const response = await fetch(`${API_BASE_URL}/authentication/verify`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Authentication request failed with status ${response.status}`);
  }

  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

