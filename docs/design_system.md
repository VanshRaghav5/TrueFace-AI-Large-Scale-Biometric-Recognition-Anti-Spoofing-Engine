# TrueFace AI-X — Design System

**Purpose:** Define the web dashboard's visual language, interaction patterns, reusable components, and accessibility rules.

> The approved synopsis specifies Next.js/React and Tailwind CSS, English as the initial language, readable status labels, keyboard-accessible controls, adequate contrast, clear errors, and explicit camera/microphone permission and fallback states. It does **not** prescribe a brand palette, typography, logo, or final screen layouts. The visual tokens below are proposed implementation defaults and may be adjusted by the team; do not represent them as institutionally approved branding.

---

## 1. Product design principles

1. **Trust through clarity:** Always distinguish identity matching from media authenticity.
2. **Explain decisions:** Display Allow, Step-up Verification, or Block with concise reason codes.
3. **Never hide uncertainty:** Missing, low-quality, conflicting, and unavailable signals need explicit states.
4. **Privacy by default:** Do not expose raw media, embeddings, secrets, or unnecessary personal data in the UI.
5. **Operational calm:** Security information should be clear and restrained, not alarmist.
6. **Accessible first:** Keyboard navigation, visible focus, readable labels, contrast, and explicit permission states.
7. **Consistent modality language:** Use the same terms for face, voice, liveness/PAD, manipulation, speaker verification, and audio anti-spoofing throughout the product.

## 2. Proposed visual direction

Use a clean, technical security-dashboard aesthetic: neutral surfaces, restrained blue accent, clear typography, and status colors reserved for decision states.

### 2.1 Color tokens (proposed)

| Token | Suggested value | Usage |
|---|---|---|
| `--tf-bg` | `#F6F8FB` | Main application background |
| `--tf-surface` | `#FFFFFF` | Cards, panels, dialogs |
| `--tf-surface-muted` | `#EEF2F7` | Secondary surfaces |
| `--tf-text` | `#172033` | Primary text |
| `--tf-text-muted` | `#5E6B7E` | Supporting text |
| `--tf-border` | `#DCE3EC` | Dividers and card borders |
| `--tf-primary` | `#2457C5` | Primary actions and links |
| `--tf-primary-hover` | `#1D469F` | Hover state |
| `--tf-success` | `#18794E` | Allow / successful operation |
| `--tf-warning` | `#9A5B00` | Step-up / caution |
| `--tf-danger` | `#B42318` | Block / destructive action |
| `--tf-info` | `#176B87` | Informational status |

Use color with text and/or icons; never rely on color alone. Check all foreground/background combinations for WCAG AA contrast before release. Dark mode is not specified by the synopsis and is optional, not a baseline requirement.

### 2.2 Typography (proposed)

- Use a highly legible system sans-serif stack or a bundled open font selected by the team.
- Page title: 24–30 px, semibold.
- Section title: 18–22 px, semibold.
- Card title: 15–17 px, semibold.
- Body: 14–16 px.
- Supporting metadata: 12–13 px; do not use for essential instructions or decisions.
- Use tabular numerals for scores, counts, and latency where available.
- Avoid long all-caps labels and dense paragraphs in operational views.

### 2.3 Spacing, shape, and elevation (proposed)

- Base spacing unit: 4 px; common steps 4, 8, 12, 16, 24, 32.
- Main content max width: approximately 1440 px; use responsive gutters.
- Card radius: 10–14 px; input radius: 8 px; pill radius for status chips.
- Prefer subtle borders over heavy shadows.
- Keep dense tables readable with row spacing and clear column headings.
- Use a consistent icon set and do not use icons without accessible labels where meaning is not obvious.

## 3. Application information architecture

Proposed top-level navigation:

- **Overview** — service health, recent activity summary, quick actions.
- **Enrollments** — consent-based enrollment and permitted reference management.
- **Authenticate** — submit/capture face and voice evidence.
- **Audit** — authorized event search and review.
- **Evaluation** — evaluator-only experiments, modality comparisons, and aggregate metrics.
- **Settings / System** — model versions, environment and account/session controls as appropriate.

Navigation visibility and access must follow backend roles. Hiding a link is not authorization; the API must enforce permissions.

## 4. Core screens and layout guidance

### 4.1 Overview
- Show API/service health and loaded model versions.
- Show aggregate counts or recent event summaries only when backed by real data.
- Do not invent sample metrics in production UI; use clearly labeled demo fixtures in development.
- Include direct links to enrollment and authentication workflows.

### 4.2 Enrollment
- Show consent notice before any sample capture/upload.
- Explain accepted media types, file size/duration limits, and whether face, voice, or both are required.
- Separate face and voice sample controls.
- Show validation and quality feedback before submission.
- Clearly state whether raw media is transient or retained under an approved policy.
- Confirm enrollment with an internal identity/reference ID; avoid exposing raw embeddings.

### 4.3 Authentication
- Provide separate face and voice capture/upload areas.
- Show camera/microphone permission status and a manual upload fallback if supported.
- Show input validation and quality checks before inference.
- Allow an optional claimed identity only where the API supports it.
- Provide an explicit submit action and loading/progress state.
- Do not show a successful result until the backend returns it.

### 4.4 Authentication result
Use a clear decision header:
- **Allow**
- **Step-up Verification**
- **Block**

Then show:
- Overall decision and reason codes.
- Face section: identity match result/score, liveness/PAD result, manipulation result.
- Voice section: speaker verification result/score, audio anti-spoof result.
- Modality availability and any skipped/failed checks.
- Latency and model versions where available.
- A short explanation of next action.

Do not collapse all scores into one unlabeled “confidence” number. Do not imply that a high identity score means the media is genuine.

### 4.5 Audit
- Restrict to authorized administrator/evaluator roles.
- Support filters such as date range and decision only when the API supports them.
- Display event ID, timestamp, decision, reason codes, model versions, and latency.
- Do not display raw media or full embeddings in audit rows.
- Provide empty, loading, error, and access-denied states.

### 4.6 Evaluation
- Show face-only, voice-only, and fused modes side by side.
- Include dataset split, model/version, threshold, and experiment configuration.
- Provide ROC/DET, confusion matrix, and other appropriate plots only when supported by actual evaluation output.
- Label validation and test results distinctly.
- Never present proposed targets as measured results.

## 5. Reusable UI components

### `DecisionBadge`
Props: `decision` (`allow | step_up | block | error`), optional label.
- Include text, not color alone.
- Use success, warning, danger, or neutral treatment respectively.
- Error is not equivalent to Block; preserve the distinction.

### `ModalityResultCard`
Props: modality, availability, identity result, authenticity checks, score fields, reason codes.
- Face and voice cards use a consistent structure.
- Display unavailable/failed checks explicitly.
- Never substitute zero for a missing score.

### `ReasonCodeList`
- Human-readable descriptions mapped from stable backend reason codes.
- Unknown codes should display a safe generic fallback plus the raw code for authorized debugging where appropriate.
- Do not expose internal stack traces.

### `MediaInputPanel`
- Separate face and voice inputs.
- Display accepted formats, size/duration rules, permission state, upload progress, validation, and retry.
- Never upload automatically on file selection unless the user explicitly confirms.

### `QualityStatus`
- States: `pending`, `valid`, `low_quality`, `invalid`, `unavailable`, `error`.
- Explain what the user can do next.

### `MetricCard`
- Label, value, unit, dataset split, and optional comparison.
- Include context and sample size where available.
- Use “Not measured” rather than fabricated values.

### `AuditTable`
- Accessible column headers, pagination, loading/empty/error states.
- Avoid raw biometric data.

### `ModelVersionLabel`
- Show model name/version or “Unavailable”.
- Distinguish loaded runtime version from experiment version.

### `PermissionNotice`
- Explicit camera/microphone permission request and denial states.
- Provide a supported fallback path or explain why the workflow cannot continue.

## 6. Interaction and state rules

Every data-driven screen should implement:
- Initial/loading state.
- Success state.
- Empty state.
- Validation-error state.
- Network/server-error state.
- Permission-denied state where relevant.
- Retry or recovery action where safe.
- Disabled state while a request is in progress.

Do not:
- Convert API errors into successful/Allow UI states.
- Hide failed or unavailable modalities.
- Automatically retry destructive or enrollment actions.
- Display stale results as if they belong to a new attempt.
- Use a score without a label, scale, and interpretation.
- Show a “green” state solely because an identity matched.

## 7. Accessibility and responsive behavior

- All actions must be keyboard accessible.
- Maintain a visible focus indicator.
- Use semantic headings, labels, buttons, tables, and form controls.
- Associate validation text with its input.
- Announce asynchronous decision changes to assistive technology.
- Ensure status meaning is communicated in text.
- Maintain adequate contrast and readable type.
- Do not rely on hover-only information.
- On small screens, stack modality cards and allow tables to scroll or switch to a readable card representation.
- Respect reduced-motion preferences.

## 8. Content and terminology

Use these exact terms consistently:
- **Face identity verification**
- **Face liveness / presentation-attack detection (PAD)**
- **Face manipulation detection**
- **Speaker verification**
- **Audio anti-spoofing**
- **Fusion / risk engine**
- **Allow**
- **Step-up Verification**
- **Block**

Prefer “potentially manipulated” over definitive language such as “fake” unless the model/task label specifically supports that wording. Say “supported attack types” rather than “all attacks”.

## 9. Frontend implementation conventions

- Stack in synopsis: Next.js, React, Tailwind CSS.
- Build shared components rather than duplicating decision logic in pages.
- Keep API response types in a shared typed module.
- Keep reason-code-to-copy mapping centralized.
- Do not calculate the security decision in the browser; the backend fusion/risk engine is authoritative.
- Keep secrets and service credentials out of client bundles.
- Use fixtures only in an explicitly marked development/demo mode.
- Add component and end-to-end tests for critical journeys.

## 10. Design decisions still open

- Final logo and brand identity.
- Final color palette and typography.
- Dark mode requirement.
- Exact navigation and page layout.
- Camera capture implementation and browser support.
- Final score visualization and charting library.
- Final responsive breakpoints.
- Final copy for consent, retention, and privacy notices after policy review.
