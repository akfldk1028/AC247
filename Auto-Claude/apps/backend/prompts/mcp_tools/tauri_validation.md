## TAURI APP VALIDATION

For Tauri desktop applications, validate both the web frontend and the Rust backend independently.

### Frontend Validation (Puppeteer)

Tauri apps use a web frontend. Start the dev server and validate with Puppeteer.

#### Step 1: Start Frontend Dev Server

```bash
# Start the frontend dev server (typically Vite on port 1420)
npm run dev &

# Wait for server to be ready
sleep 10
```

#### Step 2: Navigate and Screenshot

```
Tool: mcp__puppeteer__puppeteer_navigate
Args: {"url": "http://localhost:1420"}
```

```
Tool: mcp__puppeteer__puppeteer_screenshot
Args: {"name": "tauri-frontend-initial"}
```

#### Step 3: Verify UI Elements

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.getElementById('root') !== null || document.getElementById('app') !== null"}
```

#### Step 4: Test Interactions

```
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "[data-testid=\"submit-button\"]"}
```

#### Step 5: Check Console Errors

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "window.__consoleErrors || []"}
```

#### Step 6: Cleanup

```bash
kill $(lsof -ti:1420) 2>/dev/null || true
```

### Rust Backend Validation

```bash
# Check Rust code compiles
cd src-tauri && cargo check

# Run Rust unit tests
cd src-tauri && cargo test

# Full Tauri build verification
cargo tauri build 2>&1 | tail -20
```

### Frontend Static Analysis

```bash
# TypeScript type checking
npx tsc --noEmit

# Lint
npm run lint 2>/dev/null || true

# Frontend tests
npm test 2>/dev/null || true
```

### Document Findings

```
TAURI VALIDATION:
- Frontend (Web):
  - Dev server started: YES/NO
  - Screenshots captured: [list]
  - UI rendered correctly: PASS/FAIL
  - Console errors: [list or "None"]
  - Interactions working: PASS/FAIL
- Rust Backend:
  - cargo check: PASS/FAIL
  - cargo test: PASS/FAIL (X/Y tests)
  - Compilation warnings: [count or "None"]
- Build Verification:
  - cargo tauri build: PASS/FAIL
  - Build errors: [list or "None"]
- Issues: [list or "None"]
```

### Handling Common Issues

**Tauri CLI Not Installed:**
1. Install: `cargo install tauri-cli`
2. Or use: `npx @tauri-apps/cli build`
3. If unavailable, fall back to separate frontend + Rust validation

**System Dependencies Missing:**
Tauri requires system libraries (GTK, WebKitGTK on Linux). If build fails due to missing system deps:
1. Document: "Tauri build skipped - missing system dependencies"
2. Validate frontend and Rust backend independently
3. Add to QA report as "Manual verification required"

**Rust Toolchain Not Installed:**
If `cargo` is not available:
1. Document: "Rust validation skipped - cargo not in PATH"
2. Validate frontend only via Puppeteer
3. Recommend Rust toolchain installation
