import type { Metadata } from "next";
import Link from "next/link";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "TrueFace AI-X — Biometric Authentication Engine",
  description: "Academic prototype for multimodal biometric verification and anti-spoofing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-tf-bg text-tf-text">
        <header className="h-16 border-b border-tf-border bg-tf-surface px-6 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-8">
            <Link href="/" className="font-bold text-lg text-tf-primary flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-tf-primary"></span>
              TrueFace AI-X
            </Link>
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-tf-text-muted">
              <Link href="/dashboard" className="hover:text-tf-primary transition-colors">Dashboard</Link>
              <Link href="/enrollment" className="hover:text-tf-primary transition-colors">Enrollment</Link>
              <Link href="/authentication" className="hover:text-tf-primary transition-colors">Authentication</Link>
              <Link href="/audit" className="hover:text-tf-primary transition-colors">Audit Logs</Link>
              <Link href="/evaluation" className="hover:text-tf-primary transition-colors">Evaluation</Link>
              <Link href="/settings" className="hover:text-tf-primary transition-colors">Settings</Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-tf-surface-muted text-tf-text-muted border border-tf-border">
              Academic Prototype
            </span>
          </div>
        </header>
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">
          {children}
        </main>
      </body>
    </html>
  );
}

