import type { Metadata } from "next";
import Link from "next/link";
import "../styles/globals.css";
import { ShieldCheck, LayoutDashboard, UserPlus, Shield, FileText, Activity, Settings } from "lucide-react";

export const metadata: Metadata = {
  title: "TrueFace AI-X — Advanced Biometric Security",
  description: "Next-generation multimodal biometric verification with AI-powered anti-spoofing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen relative overflow-x-hidden">
        {/* Animated purple gradient orbs background */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
          <div className="absolute top-0 -left-4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: "0s" }}></div>
          <div className="absolute top-20 right-10 w-80 h-80 bg-purple-500/8 rounded-full blur-3xl animate-float" style={{ animationDelay: "2s" }}></div>
          <div className="absolute bottom-10 left-1/3 w-72 h-72 bg-violet-500/6 rounded-full blur-3xl animate-float" style={{ animationDelay: "4s" }}></div>
        </div>

        {/* Modern hardware header */}
        <header className="sticky top-0 z-50 panel border-b border-tf-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo */}
              <Link href="/" className="flex items-center gap-3 group">
                <div className="w-10 h-10 bg-tf-surface border border-tf-border flex items-center justify-center group-hover:border-tf-accent transition-colors">
                  <ShieldCheck className="w-6 h-6 text-tf-accent" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">TrueFace AI-X</h1>
                  <p className="text-xs text-gray-500 font-mono -mt-0.5 uppercase tracking-wider">Biometric Security</p>
                </div>
              </Link>

              {/* Navigation */}
              <nav className="hidden md:flex items-center gap-1">
                <NavLink href="/dashboard" icon={<LayoutDashboard className="w-4 h-4" />}>Dashboard</NavLink>
                <NavLink href="/enrollment" icon={<UserPlus className="w-4 h-4" />}>Enrollment</NavLink>
                <NavLink href="/authentication" icon={<Shield className="w-4 h-4" />}>Verify</NavLink>
                <NavLink href="/audit" icon={<FileText className="w-4 h-4" />}>Audit</NavLink>
                <NavLink href="/evaluation" icon={<Activity className="w-4 h-4" />}>Eval</NavLink>
                <NavLink href="/settings" icon={<Settings className="w-4 h-4" />}>Settings</NavLink>
              </nav>

              {/* Status badge */}
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 panel border border-tf-border">
                  <div className="w-2 h-2 bg-tf-accent"></div>
                  <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">Academic</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="relative z-10 mt-20 border-t border-tf-border panel">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-sm text-gray-500">
              <p className="font-mono">TrueFace AI-X © {new Date().getFullYear()} — MULTIMODAL BIOMETRIC RESEARCH PLATFORM</p>
              <p className="text-xs mt-1 text-gray-600">FOR RESEARCH AND ACADEMIC USE ONLY</p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

function NavLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 px-4 py-2 text-sm font-mono text-gray-400 hover:text-tf-accent hover:bg-tf-surface transition-all uppercase tracking-wider"
    >
      <span className="text-gray-600 group-hover:text-tf-accent transition-colors">{icon}</span>
      {children}
    </Link>
  );
}
