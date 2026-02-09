## TAURI APP VALIDATION

For Tauri desktop applications, validate both the web frontend and the Rust backend independently.

**CRITICAL**: You MUST use Playwright MCP tools for frontend validation. `curl` or code review alone is NOT sufficient.

### Frontend Validation (Playwright — MANDATORY)

Tauri apps use a web frontend. You MUST start the dev server and validate with Playwright.

#### Step 1: Start Frontend Dev Server (MANDATORY)

Use the `dev_command` from **DEV SERVER CONFIGURATION** (injected above in the prompt).
If not available, check `project_index.json` or use the project's dev script (typically `npm run dev`).

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev"
```

**Linux/macOS (Bash):**
```bash
npm run dev &
```

#### Step 2: Wait for Server Ready — Cross-Platform Port Polling (MANDATORY)

**Do NOT use `sleep 10` or any fixed sleep.** Poll the port until the server is listening.

Use the health check commands from DEV SERVER CONFIGURATION, or:

**Windows (PowerShell):**
```powershell
$port = 1420; $timeout = 60; $elapsed = 0
while ($elapsed -lt $timeout) {
  try { $tcp = New-Object System.Net.Sockets.TcpClient('localhost', $port); $tcp.Close(); break }
  catch { Start-Sleep -Seconds 2; $elapsed += 2 }
}
```

**Linux/macOS (Bash):**
```bash
port=1420; timeout=60; elapsed=0
while [ $elapsed -lt $timeout ]; do
  curl -s http://localhost:$port > /dev/null 2>&1 && break
  sleep 2; elapsed=$((elapsed + 2))
done
```

Replace port with the actual port from DEV SERVER CONFIGURATION.

#### Step 3: Navigate and Take Snapshot (MANDATORY — MUST CALL THESE TOOLS)

You MUST call these Playwright tools. Do NOT substitute with curl or wget.

```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:PORT"}
```

```
Tool: mcp__playwright__browser_snapshot
```

Get the accessibility tree to discover interactive elements.

#### Step 4: Take Screenshot and SAVE (MANDATORY — MUST CALL THIS TOOL)

```bash
mkdir -p screenshots
```

```
Tool: mcp__playwright__browser_take_screenshot
Args: {"fileName": "screenshots/01-initial-load"}
```

Capture the page for visual verification. Compare against spec requirements.
Save additional screenshots after interactions: `screenshots/02-after-{action}`

#### Step 5: Test Interactions (MANDATORY for interactive apps)

Use `ref` values from the accessibility snapshot:

```
Tool: mcp__playwright__browser_click
Args: {"element": "Submit button", "ref": "e1"}
```

```
Tool: mcp__playwright__browser_type
Args: {"element": "Text input", "ref": "e2", "text": "test value"}
```

After each interaction, take a new snapshot or screenshot to verify the result.

#### Step 6: Check Console Errors (MANDATORY — MUST CALL THIS TOOL)

```
Tool: mcp__playwright__browser_console_messages
```

Check for JavaScript errors, framework warnings, or Tauri API call failures.

#### Step 7: Cleanup (MANDATORY)

**Windows (PowerShell):**
```powershell
Get-NetTCPConnection -LocalPort PORT -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

**Linux/macOS (Bash):**
```bash
kill $(lsof -ti:PORT) 2>/dev/null || true
```

Replace `PORT` with the actual port.

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

### Document Findings (MANDATORY)

```
TAURI VALIDATION:
- Frontend (Web):
  - Dev server started: YES/NO
  - Playwright navigate called: YES/NO
  - Playwright snapshot called: YES/NO
  - Playwright screenshot called: YES/NO
  - Screenshots captured: [count]
  - UI rendered correctly: PASS/FAIL
  - Console errors: [list or "None"]
  - Interactions tested: [list]
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

**IMPORTANT**: If Playwright tools were not called, Frontend validation MUST be INCOMPLETE, not PASS.

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
2. Validate frontend only via Playwright (STILL MANDATORY)
3. Recommend Rust toolchain installation
