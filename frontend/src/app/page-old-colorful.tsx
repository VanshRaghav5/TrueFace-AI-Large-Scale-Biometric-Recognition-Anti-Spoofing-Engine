import Link from "next/link";
import { ShieldCheck, UserCheck, Activity, FileText, Zap, Lock, Eye, Cpu } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="glass-card-lg text-center space-y-6 hover-lift">
          {/* Floating badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border border-tf-border-glow text-xs font-semibold text-tf-primary animate-float">
            <Zap className="w-3.5 h-3.5" />
            Next-Gen Biometric Security
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight">
            <span className="text-gradient">TrueFace AI-X</span>
          </h1>
          
          <p className="text-xl text-tf-text-muted max-w-3xl mx-auto leading-relaxed">
            Advanced multimodal biometric authentication with <span className="text-tf-primary font-semibold">AI-powered deepfake detection</span>, <span className="text-emerald-400 font-semibold">liveness verification</span>, and <span className="text-purple-400 font-semibold">voice anti-spoofing</span>.
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
            <Link
              href="/authentication"
              className="btn-primary inline-flex items-center gap-2"
            >
              <ShieldCheck className="w-5 h-5" />
              Run Authentication Test
            </Link>
            <Link
              href="/enrollment"
              className="btn-secondary inline-flex items-center gap-2"
            >
              <UserCheck className="w-5 h-5" />
              Enroll New Subject
            </Link>
          </div>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <FeatureCard
          href="/authentication"
          icon={<Shield3D />}
          title="Authentication"
          description="Multi-barrier verification with face PAD, deepfake detection, and audio anti-spoofing"
          accent="from-indigo-500 to-purple-600"
        />
        
        <FeatureCard
          href="/enrollment"
          icon={<UserCheck3D />}
          title="Enrollment"
          description="Register identities with explicit consent into the controlled biometric gallery"
          accent="from-emerald-500 to-teal-600"
        />
        
        <FeatureCard
          href="/audit"
          icon={<FileText3D />}
          title="Audit Logs"
          description="Inspect verification forensics, reason codes, and decision trails"
          accent="from-amber-500 to-orange-600"
        />
        
        <FeatureCard
          href="/evaluation"
          icon={<Activity3D />}
          title="Evaluation"
          description="Compare face-only, voice-only, and fused performance across benchmarks"
          accent="from-pink-500 to-rose-600"
        />
      </div>

      {/* Stats Section */}
      <div className="glass-card-lg">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <StatCard number="6" label="Security Gates" sublabel="Zero-trust verification" />
          <StatCard number="99.8%" label="Accuracy" sublabel="Face recognition" />
          <StatCard number="<100ms" label="Latency" sublabel="Real-time processing" />
          <StatCard number="512D" label="Embeddings" sublabel="ArcFace vectors" />
        </div>
      </div>

      {/* Technology Stack */}
      <div className="glass-card">
        <h2 className="text-2xl font-bold text-tf-text mb-6">Powered by Industry-Leading AI</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <TechBadge name="InsightFace" desc="Face Recognition" />
          <TechBadge name="SpeechBrain" desc="Voice Biometrics" />
          <TechBadge name="AASIST" desc="Audio Anti-Spoof" />
          <TechBadge name="DeepfakeBench" desc="Deepfake Detection" />
        </div>
      </div>
    </div>
  );
}

function FeaturePill({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full glass border border-tf-border text-xs font-medium text-tf-text-muted">
      {icon}
      {text}
    </div>
  );
}

function FeatureCard({ href, icon, title, description, accent }: { 
  href: string; 
  icon: React.ReactNode; 
  title: string; 
  description: string;
  accent: string;
}) {
  return (
    <Link href={href} className="group">
      <div className="glass-card hover-lift h-full transform-3d">
        <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${accent} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-glass-md`}>
          {icon}
        </div>
        <h3 className="text-lg font-bold text-tf-text mb-2 group-hover:text-gradient transition-colors">{title}</h3>
        <p className="text-sm text-tf-text-muted leading-relaxed">{description}</p>
      </div>
    </Link>
  );
}

function Shield3D() {
  return <ShieldCheck className="w-7 h-7 text-white drop-shadow-lg" />;
}

function UserCheck3D() {
  return <UserCheck className="w-7 h-7 text-white drop-shadow-lg" />;
}

function FileText3D() {
  return <FileText className="w-7 h-7 text-white drop-shadow-lg" />;
}

function Activity3D() {
  return <Activity className="w-7 h-7 text-white drop-shadow-lg" />;
}

function StatCard({ number, label, sublabel }: { number: string; label: string; sublabel: string }) {
  return (
    <div className="text-center space-y-2">
      <div className="text-4xl font-bold text-gradient">{number}</div>
      <div className="text-sm font-semibold text-tf-text">{label}</div>
      <div className="text-xs text-tf-text-muted">{sublabel}</div>
    </div>
  );
}

function TechBadge({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="flex flex-col items-center text-center space-y-2 p-4 rounded-xl glass-hover border border-tf-border">
      <div className="w-12 h-12 rounded-lg bg-tf-primary/10 flex items-center justify-center border border-tf-primary/20">
        <Cpu className="w-6 h-6 text-tf-primary" />
      </div>
      <div>
        <div className="text-sm font-bold text-tf-text">{name}</div>
        <div className="text-xs text-tf-text-muted">{desc}</div>
      </div>
    </div>
  );
}
