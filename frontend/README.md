# TrueFace AI-X Frontend

Modern Next.js 14 dashboard with hardware-inspired UI for multimodal biometric authentication.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** Custom React components
- **Charts:** Recharts
- **Icons:** Lucide React
- **Animation:** Lottie (voice wave visualization)

## Architecture

```
frontend/
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── layout.tsx              # Root layout with navigation
│   │   ├── page.tsx                # Home page
│   │   ├── dashboard/              # System status dashboard
│   │   ├── enrollment/             # Biometric enrollment interface
│   │   ├── authentication/         # Verification interface
│   │   ├── audit/                  # Audit log viewer
│   │   ├── evaluation/             # Performance metrics
│   │   └── settings/               # Threshold configuration
│   │
│   ├── components/                 # Reusable components
│   │   ├── VoiceWave.tsx           # Voice recording animation
│   │   ├── TerminalLog.tsx         # Real-time event console
│   │   ├── CameraPreview.tsx       # Camera viewfinder with brackets
│   │   ├── MetricDisplay.tsx       # Monospace telemetry panels
│   │   ├── StatusBadge.tsx         # Hardware-style status badges
│   │   ├── FileDropZone.tsx        # Drag-and-drop file upload
│   │   ├── PipelineStepper.tsx     # 6-gate progress indicator
│   │   ├── VerificationStages.tsx  # Stage animations
│   │   └── charts/                 # Data visualizations
│   │       ├── ROCCurve.tsx
│   │       ├── PerformanceComparison.tsx
│   │       ├── LatencySparkline.tsx
│   │       ├── CircularGauge.tsx
│   │       └── VolumeChart.tsx
│   │
│   └── styles/
│       └── globals.css             # Global styles & utility classes
│
├── public/                         # Static assets
├── package.json                    # Dependencies
├── tailwind.config.ts              # Tailwind configuration
└── tsconfig.json                   # TypeScript configuration
```

## Design System

### Color Palette
- **Background:** `#0a0a0a` (deep black)
- **Surface:** `#1a1a1a` (dark charcoal) with subtle glass effect
- **Border:** `#2a2a2a` (crisp grey)
- **Accent:** `#10b981` (emerald green) - only for verified/active states
- **Alert:** `#f97316` (safety orange)
- **Purple orbs:** Animated background (10%, 8%, 6% opacity)

### Typography
- **Body:** Inter, system-ui, sans-serif
- **Telemetry:** JetBrains Mono, Fira Code (monospace)
- **Features:** Tabular numerals with slashed zeros

### Surface Style
- **Panels:** Flat matte with 1px borders and subtle backdrop blur
- **Corners:** Sharp 2px radius (hardware aesthetic)
- **No shadows:** Flat design philosophy
- **Glass effect:** Subtle `backdrop-filter: blur(8px)`

### Components

#### Badges
- `.badge-verified` - Emerald with emerald border
- `.badge-scanning` - Yellow with pulsing animation
- `.badge-denied` - Orange with orange border

#### Buttons
- `.btn-primary` - Emerald background, black text
- `.btn-secondary` - Transparent with border

#### Panels
- `.panel` - Base glass panel with blur
- `.terminal` - Monospace log console
- `.metric` - Large monospace numbers

## Pages

### Home (`/`)
Four monochrome feature cards with emerald hover effect showcasing system capabilities.

### Dashboard (`/dashboard`)
- System health status
- Model runtime details
- CPU/Memory gauges
- 24h verification volume chart
- Real-time latency sparklines

### Enrollment (`/enrollment`)
- Subject ID input
- Face capture (upload or live camera)
- Voice recording (upload or record)
- Security PIN (optional)
- Enrolled subjects gallery

### Authentication (`/authentication`)
- Asymmetric layout (large camera left, metrics/log right)
- 6-gate pipeline progress stepper
- Individual gate check buttons
- Real-time terminal log
- Verification stage animations

### Audit (`/audit`)
- Verification history table
- Decision distribution donut chart
- Visual score bars
- Color-coded decision badges
- Reason code pills

### Evaluation (`/evaluation`)
- ROC curve visualization
- Performance comparison charts (EER, APCER, BPCER)
- Metric cards (accuracy, FAR, FRR)
- Run benchmark button

### Settings (`/settings`)
- Interactive threshold sliders
- Score distribution visualization
- Genuine vs Impostor curves
- Dynamic threshold overlay

## Development

### Setup
```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Environment Variables
Create `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Component Development
```tsx
// Example: Create new chart component
import { LineChart, Line, XAxis, YAxis } from 'recharts';

export default function MyChart({ data }) {
  return (
    <div className="panel p-6">
      <h3 className="text-sm font-mono uppercase tracking-wider text-gray-400 mb-4">
        Chart Title
      </h3>
      <LineChart width={600} height={300} data={data}>
        <XAxis dataKey="name" stroke="#6b7280" />
        <YAxis stroke="#6b7280" />
        <Line type="monotone" dataKey="value" stroke="#10b981" />
      </LineChart>
    </div>
  );
}
```

### Styling Guidelines
```tsx
// Use utility classes from globals.css
<div className="panel">              {/* Glass panel */}
  <div className="telemetry">         {/* Monospace font */}
    <div className="metric">87</div>  {/* Large number */}
    <div className="badge-verified">  {/* Status badge */}
      VERIFIED
    </div>
  </div>
</div>

// Monospace telemetry
<span className="font-mono tabular-nums">
  {latency.toFixed(1)} ms
</span>
```

## API Integration

### Fetch Example
```typescript
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 
                "http://localhost:8000/api/v1";

async function verifyBiometric(faceImage: File, voiceSample?: File) {
  const formData = new FormData();
  formData.append("face_image", faceImage);
  if (voiceSample) {
    formData.append("voice_sample", voiceSample);
  }

  const response = await fetch(`${apiBase}/authentication/verify`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Verification failed");
  }

  return await response.json();
}
```

## Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

## Build Optimization

Current build sizes:
```
Route (app)                Size     First Load JS
├ /                       2.82 kB   98.9 kB
├ /audit                  9.25 kB   198 kB
├ /authentication        11.1 kB    98.5 kB
├ /dashboard              4.34 kB   226 kB
├ /enrollment             8.93 kB   96.3 kB
├ /evaluation            14.8 kB    230 kB
└ /settings               2.25 kB   224 kB
```

### Optimization Tips
- Use dynamic imports for heavy components
- Optimize images with Next.js Image
- Code split charts and visualizations
- Lazy load non-critical components

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Accessibility
- WCAG 2.1 AA compliance target
- Keyboard navigation support
- Screen reader friendly
- High contrast mode support

## Documentation
- [Design System](../docs/design_system.md)
- [Frontend Modernization](../docs/frontend/frontend_modernization.md)
- [Purple Theme](../docs/frontend/purple_theme_voice_animation.md)

## License
Academic research use only. See project root for full license.
