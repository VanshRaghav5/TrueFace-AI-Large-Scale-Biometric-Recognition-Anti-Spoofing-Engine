"use client";

import Link from "next/link";
import { ShieldCheck, UserCheck, Activity, FileText, Zap, Lock, Eye, Cpu } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen p-6 space-y-12">
      {/* Hero Section */}
      <div className="panel p-12 text-center space-y-8">
        {/* Floating badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 border border-tf-border text-xs font-mono uppercase tracking-wider text-gray-400">
          <Zap className="w-3.5 h-3.5" />
          Next-Gen Biometric Security
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-white">
          TrueFace AI-X
        </h1>
        
        <p className="text-lg text-gray-400 max-w-3xl mx-auto leading-relaxed font-mono">
          Advanced multimodal biometric authentication with <span className="text-tf-accent">AI-powered deepfake detection</span>, <span className="text-tf-accent">liveness verification</span>, and <span className="text-tf-accent">voice anti-spoofing</span>.
        </p>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-3 pt-4">
          <FeaturePill icon={<Eye className="w-3.5 h-3.5" />} text="Face Recognition" />
          <FeaturePill icon={<Cpu className="w-3.5 h-3.5" />} text="Voice Biometrics" />
          <FeaturePill icon={<Lock className="w-3.5 h-3.5" />} text="Anti-Spoofing" />
          <FeaturePill icon={<ShieldCheck className="w-3.5 h-3.5" />} text="Zero-Trust" />
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-wrap justify-center gap-4 pt-6">
          <Link href="/authentication" className="btn-primary inline-flex items-center gap-2">
            <ShieldCheck className="w-5 h-5" />
            Run Authentication Test
          </Link>
          <Link href="/enrollment" className="btn-secondary inline-flex items-center gap-2">
            <UserCheck className="w-5 h-5" />
            Enroll New Subject
          </Link>
        </div>
      </div>

      {/* Feature Cards Grid - Monochrome with hover accent */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <FeatureCard
          href="/authentication"
          icon={<ShieldCheck className="w-7 h-7" />}
          title="Authentication"
          description="Multi-barrier verification with face PAD, deepfake detection, and audio anti-spoofing"
        />
        
        <FeatureCard
          href="/enrollment"
          icon={<UserCheck className="w-7 h-7" />}
          title="Enrollment"
          description="Register identities with explicit consent into the controlled biometric gallery"
        />
        
        <FeatureCard
          href="/audit"
          icon={<FileText className="w-7 h-7" />}
          title="Audit Logs"
          description="Inspect verification forensics, reason codes, and decision trails"
        />
        
        <FeatureCard
          href="/evaluation"
          icon={<Activity className="w-7 h-7" />}
          title="Evaluation"
          description="Compare face-only, voice-only, and fused performance across benchmarks"
        />
      </div>

      {/* Stats Section */}
      <div className="panel p-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <StatCard number="6" label="Security Gates" sublabel="Zero-trust verification" />
          <StatCard number="99.8%" label="Accuracy" sublabel="Face recognition" />
          <StatCard number="<100ms" label="Latency" sublabel="Real-time processing" />
          <StatCard number="512D" label="Embeddings" sublabel="Vector space" />
        </div>
      </div>

      {/* Technology Stack - No library names */}
      <div className="panel p-8">
        <h2 className="text-xl font-mono uppercase tracking-wider text-gray-400 mb-6">Powered by Industry-Leading AI</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <TechBadge name="Face Recognition" desc="Detection & matching" />
          <TechBadge name="Voice Biometrics" desc="Speaker verification" />
          <TechBadge name="Audio Anti-Spoof" desc="Synthetic detection" />
          <TechBadge name="Deepfake Detection" desc="Manipulation analysis" />
        </div>
      </div>
    </div>
  );
}

function FeaturePill({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 border border-tf-border text-xs font-mono text-gray-500">
      {icon}
      {text}
    </div>
  );
}

function FeatureCard({ href, icon, title, description }: { 
  href: string; 
  icon: React.ReactNode; 
  title: string; 
  description: string;
}) {
  return (
    <Link href={href} className="group">
      <div className="panel p-6 h-full transition-all duration-200 hover:border-tf-accent">
        {/* Monochrome icon box with emerald on hover */}
        <div className="w-14 h-14 border border-tf-border flex items-center justify-center mb-4 group-hover:border-tf-accent transition-colors text-gray-500 group-hover:text-tf-accent">
          {icon}
        </div>
        <h3 className="text-lg font-mono uppercase tracking-wider text-white mb-2 group-hover:text-tf-accent transition-colors">
          {title}
        </h3>
        <p className="text-sm text-gray-500 leading-relaxed font-mono">{description}</p>
      </div>
    </Link>
  );
}

function StatCard({ number, label, sublabel }: { number: string; label: string; sublabel: string }) {
  return (
    <div className="text-center space-y-2">
      <div className="text-4xl font-mono font-bold text-tf-accent telemetry">{number}</div>
      <div className="text-sm font-mono uppercase tracking-wider text-white">{label}</div>
      <div className="text-xs text-gray-600 font-mono">{sublabel}</div>
    </div>
  );
}

function TechBadge({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="flex flex-col items-center text-center space-y-2 panel p-4 hover:border-tf-accent transition-colors">
      <div className="w-12 h-12 border border-tf-border flex items-center justify-center">
        <Cpu className="w-6 h-6 text-gray-500" />
      </div>
      <div>
        <div className="text-sm font-mono text-white">{name}</div>
        <div className="text-xs text-gray-600 font-mono">{desc}</div>
      </div>
    </div>
  );
}
