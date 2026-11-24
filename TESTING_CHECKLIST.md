# TrueFace AI-X Testing Checklist

Complete verification checklist for all features and components.

## ✅ Pre-Deployment Checklist

### Environment Setup
- [ ] Single `venv/` at root level exists
- [ ] `requirements.txt` consolidated
- [ ] `.env` configured correctly
- [ ] Database migrations applied
- [ ] Models downloaded and accessible

### Backend Services
- [ ] Backend starts without errors
- [ ] Health endpoint returns 200
- [ ] All models show "ready" status
- [ ] Database connection successful
- [ ] FAISS index builds correctly

### Frontend Services
- [ ] Frontend builds successfully
- [ ] No TypeScript errors
- [ ] All pages accessible
- [ ] API connection works
- [ ] Charts render correctly

---

## 🧪 Backend API Testing

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```
- [ ] Returns JSON with model status
- [ ] Face model: "ready"
- [ ] Database: "ready"
- [ ] Response time < 100ms

### Enrollment
```bash
# Test with sample image
curl -X POST http://localhost:8000/api/v1/enrollment \
  -F "subject_id=test_user_001" \
  -F "consent_confirmed=true" \
  -F "face_image=@test_face.jpg"
```
- [ ] Successful enrollment returns 200
- [ ] Subject ID stored in database
- [ ] Face template extracted (512-d)
- [ ] FAISS index updated
- [ ] Audit event created

### Face Verification
```bash
curl -X POST http://localhost:8000/api/v1/face/verify \
  -F "face_image=@test_face.jpg" \
  -F "claimed_subject_id=test_user_001"
```
- [ ] Returns similarity score
- [ ] Recognition state: "known" or "unknown"
- [ ] Processing time < 200ms
- [ ] Reason codes present

### PAD (Liveness)
```bash
curl -X POST http://localhost:8000/api/v1/face/pad \
  -F "face_image=@test_face.jpg"
```
- [ ] Returns "real" or "attack" state
- [ ] Real score and spoof score present
- [ ] Processing time < 150ms

### Deepfake Detection
```bash
curl -X POST http://localhost:8000/api/v1/face/deepfake \
  -F "face_image=@test_face.jpg"
```
- [ ] Returns authenticity score
- [ ] State: "authentic" or "manipulated"
- [ ] Processing time < 150ms

### Voice Verification
```bash
curl -X POST http://localhost:8000/api/v1/voice/verify \
  -F "voice_sample=@test_audio.wav" \
  -F "claimed_subject_id=test_user_001"
```
- [ ] Returns similarity score
- [ ] Speech detection works
- [ ] Processing time < 300ms

### Full Authentication
```bash
curl -X POST http://localhost:8000/api/v1/authentication/verify \
  -F "face_image=@test_face.jpg" \
  -F "voice_sample=@test_audio.wav" \
  -F "claimed_subject_id=test_user_001" \
  -F "security_pin=123456"
```
- [ ] Returns overall decision
- [ ] Identity score computed
- [ ] Authenticity score computed
- [ ] All gates checked
- [ ] Reason codes present
- [ ] Total latency < 500ms

### Audit Logs
```bash
curl http://localhost:8000/api/v1/audit
```
- [ ] Returns audit event list
- [ ] Events include timestamps
- [ ] Decision outcomes logged
- [ ] Scores recorded

---

## 🎨 Frontend UI Testing

### Home Page (`/`)
- [ ] Page loads without errors
- [ ] Four feature cards visible
- [ ] Hover effects work (emerald accent)
- [ ] Navigation links functional
- [ ] Purple background orbs visible
- [ ] Grid pattern subtle

### Dashboard (`/dashboard`)
- [ ] Model status cards show correctly
- [ ] Face/Voice/Database status indicators
- [ ] CPU gauge renders
- [ ] Memory gauge renders
- [ ] 24h volume chart displays
- [ ] Latency sparklines visible
- [ ] Model details expandable

### Enrollment (`/enrollment`)
- [ ] Subject ID input works
- [ ] Face upload (FileDropZone) functional
- [ ] Camera capture works
- [ ] Photo preview displays
- [ ] Voice upload (FileDropZone) functional
- [ ] Voice recording works
- [ ] Recording timer displays
- [ ] Audio playback works
- [ ] PIN input functional
- [ ] Consent checkbox works
- [ ] Submit button enables/disables correctly
- [ ] Success message displays
- [ ] Enrolled subjects list updates

### Authentication (`/authentication`)
- [ ] Face upload (FileDropZone) functional
- [ ] Camera preview works with brackets
- [ ] Camera capture functional
- [ ] Voice upload (FileDropZone) functional
- [ ] Voice recording works
- [ ] Claimed ID input works
- [ ] PIN input works
- [ ] Full verification button works
- [ ] Individual gate buttons work:
  - [ ] Face Match
  - [ ] Anti-Spoof
  - [ ] Deepfake Check
  - [ ] Voice Verify
- [ ] Pipeline stepper shows 6 gates
- [ ] Pipeline updates in real-time
- [ ] Terminal log displays events
- [ ] Metrics display scores
- [ ] Status badge changes color
- [ ] Verification stages animate

### Audit (`/audit`)
- [ ] Audit table loads
- [ ] Decision badges color-coded
- [ ] Score bars visualize correctly
- [ ] Reason code pills display
- [ ] Donut chart renders
- [ ] Decision distribution accurate
- [ ] Filtering works (if implemented)
- [ ] Pagination works (if implemented)

### Evaluation (`/evaluation`)
- [ ] ROC curve renders
- [ ] Performance comparison chart displays
- [ ] Metric cards show values
- [ ] "Run Benchmark" button works
- [ ] Charts update with data

### Settings (`/settings`)
- [ ] Threshold sliders functional
- [ ] Slider values update display
- [ ] Score distribution chart renders
- [ ] Genuine vs Impostor curves display
- [ ] Threshold line moves with slider
- [ ] Save button functional

---

## 🔄 Component Testing

### FileDropZone
- [ ] Drag and drop works
- [ ] File selection dialog opens
- [ ] Selected file displays
- [ ] File size shows
- [ ] Clear button works
- [ ] Hover effects work
- [ ] Border color changes on drag

### VoiceWave
- [ ] Animation plays during recording
- [ ] Stops when recording stops
- [ ] Doesn't block other elements
- [ ] Lottie player loads

### TerminalLog
- [ ] Events display in real-time
- [ ] Timestamps correct
- [ ] Status colors correct:
  - [ ] Success: emerald
  - [ ] Error: orange
  - [ ] Info: gray
  - [ ] Processing: yellow
- [ ] Auto-scroll works
- [ ] Monospace font applied

### CameraPreview
- [ ] Video stream displays
- [ ] Corner brackets visible
- [ ] Capture button works
- [ ] Stop button works
- [ ] Viewfinder style applied

### StatusBadge
- [ ] "verified" badge: emerald
- [ ] "scanning" badge: yellow, pulsing
- [ ] "denied" badge: orange
- [ ] "idle" badge: gray
- [ ] Font styles correct

### PipelineStepper
- [ ] 6 gates display
- [ ] Status icons correct:
  - [ ] Pending: number
  - [ ] Processing: spinner
  - [ ] Success: checkmark
  - [ ] Failed: X
- [ ] Progress updates
- [ ] Connector lines color

### Charts
- [ ] ROC Curve: axes, line, labels
- [ ] Performance Comparison: bars, legend
- [ ] Latency Sparkline: line, gradient
- [ ] Circular Gauge: arc, value, label
- [ ] Volume Chart: area, gradient

---

## 🔐 Security Testing

### Input Validation
- [ ] SQL injection attempts blocked
- [ ] File type validation works
- [ ] File size limits enforced
- [ ] Malformed JSON rejected
- [ ] XSS attempts sanitized

### Authentication
- [ ] Consent required for enrollment
- [ ] Invalid subject IDs rejected
- [ ] PIN hashing works
- [ ] Session management secure

### Privacy
- [ ] No raw images stored
- [ ] No audio files persisted
- [ ] Only embeddings in database
- [ ] Audit logs anonymized (if applicable)

---

## ⚡ Performance Testing

### Latency
- [ ] Face detection: < 50ms
- [ ] Face recognition: < 100ms
- [ ] PAD: < 100ms
- [ ] Deepfake: < 150ms
- [ ] Voice recognition: < 200ms
- [ ] Full pipeline: < 500ms

### Throughput
- [ ] 10 concurrent enrollments
- [ ] 20 concurrent verifications
- [ ] No memory leaks
- [ ] CPU usage reasonable

### Database
- [ ] Query response < 50ms
- [ ] Index performance good
- [ ] Connection pooling works

---

## 🌐 Browser Compatibility

### Desktop
- [ ] Chrome 90+
- [ ] Firefox 88+
- [ ] Safari 14+
- [ ] Edge 90+

### Mobile (if applicable)
- [ ] Chrome mobile
- [ ] Safari mobile
- [ ] Responsive design

---

## 📦 Build & Deployment

### Backend
```bash
cd backend
pytest tests/
```
- [ ] All tests pass
- [ ] No warnings
- [ ] Coverage > 70%

### Frontend
```bash
cd frontend
npm test
npm run build
```
- [ ] All tests pass
- [ ] Build successful
- [ ] No TypeScript errors
- [ ] Bundle size reasonable

### Docker
```bash
docker-compose up --build
```
- [ ] All containers start
- [ ] Services communicate
- [ ] Health checks pass

---

## 📝 Documentation

### READMEs
- [ ] Root README.md comprehensive
- [ ] Backend README.md complete
- [ ] Frontend README.md complete
- [ ] Docs README.md organized

### Code Comments
- [ ] Critical functions documented
- [ ] Complex logic explained
- [ ] API endpoints documented
- [ ] Type hints present

### API Documentation
- [ ] OpenAPI schema accessible
- [ ] All endpoints documented
- [ ] Request/response examples
- [ ] Error codes explained

---

## 🚨 Error Handling

### Backend Errors
- [ ] 404: Not Found handled
- [ ] 422: Validation errors clear
- [ ] 500: Internal errors logged
- [ ] Graceful degradation

### Frontend Errors
- [ ] Network errors handled
- [ ] Loading states displayed
- [ ] Error messages clear
- [ ] Retry mechanisms work

---

## ✅ Final Verification

### Critical Path
1. [ ] Start backend: `uvicorn app.main:app`
2. [ ] Start frontend: `npm run dev`
3. [ ] Open browser: `http://localhost:3000`
4. [ ] Check dashboard: All models "READY"
5. [ ] Enroll test subject
6. [ ] Verify enrolled subject
7. [ ] Check audit logs
8. [ ] Review metrics

### Smoke Tests
- [ ] Can enroll new subject
- [ ] Can authenticate subject
- [ ] Can view audit logs
- [ ] Can adjust thresholds
- [ ] Can run evaluation

### Acceptance Criteria
- [ ] All pages load without errors
- [ ] All API endpoints functional
- [ ] All charts and visualizations work
- [ ] FileDropZone responsive
- [ ] No console errors
- [ ] Performance acceptable
- [ ] Security measures in place

---

## 📊 Test Results Summary

**Date:** ___________  
**Tester:** ___________  
**Environment:** Development / Staging / Production

| Category | Passed | Failed | Skipped | Notes |
|----------|--------|--------|---------|-------|
| Backend API | __ / __ | __ | __ | |
| Frontend UI | __ / __ | __ | __ | |
| Components | __ / __ | __ | __ | |
| Security | __ / __ | __ | __ | |
| Performance | __ / __ | __ | __ | |
| Build/Deploy | __ / __ | __ | __ | |

**Overall Status:** ☐ PASS ☐ FAIL ☐ CONDITIONAL PASS

**Blockers:** ___________

**Sign-off:** ___________
