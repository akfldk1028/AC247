## REACT NATIVE / EXPO RUNTIME VALIDATION

For React Native and Expo projects, use web mode for browser-based validation when possible, with native build verification as fallback.

**CRITICAL**: For Expo projects with web support, you MUST use Playwright MCP tools for browser verification.
`curl` or code review alone does NOT count as browser verification.

### Expo Projects (Web Mode Validation — MANDATORY when web is supported)

Expo supports web targets, enabling Playwright-based runtime validation.

#### Step 1: Start Expo Web Dev Server (MANDATORY)

Use the `dev_command` from **DEV SERVER CONFIGURATION** (injected above in the prompt).
If not available, use:

**Linux/macOS:**
```bash
npx expo start --web --port=8081 &
```

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow -FilePath "npx" -ArgumentList "expo", "start", "--web", "--port=8081"
```

#### Step 2: Wait for Server Ready — Cross-Platform Port Polling (MANDATORY)

**Do NOT use `sleep 10` or any fixed sleep.** Poll the port until the server is listening.

**Linux/macOS:**
```bash
timeout=60; elapsed=0
while [ $elapsed -lt $timeout ]; do
  curl -s http://localhost:8081 > /dev/null 2>&1 && break
  sleep 2; elapsed=$((elapsed + 2))
done
```

**Windows (PowerShell):**
```powershell
$timeout = 60; $elapsed = 0
while ($elapsed -lt $timeout) {
  try { $tcp = New-Object System.Net.Sockets.TcpClient('localhost', 8081); $tcp.Close(); break }
  catch { Start-Sleep -Seconds 2; $elapsed += 2 }
}
```

Replace port 8081 with the actual port from DEV SERVER CONFIGURATION if different.

#### Step 3: Navigate and Take Snapshot (MANDATORY — MUST CALL THESE TOOLS)

You MUST call these Playwright tools. Do NOT substitute with curl or wget.

```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:8081"}
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
Args: {"element": "Email input", "ref": "e2", "text": "test@example.com"}
```

After each interaction, take a new snapshot or screenshot to verify the result.

#### Step 6: Check Console for Errors (MANDATORY — MUST CALL THIS TOOL)

```
Tool: mcp__playwright__browser_console_messages
```

Check for JavaScript errors, framework warnings, and failed network requests.

#### Step 7: Cleanup (MANDATORY)

**Linux/macOS:**
```bash
kill $(lsof -ti:8081) 2>/dev/null || true
```

**Windows (PowerShell):**
```powershell
Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

**Note:** Some React Native components have no web equivalent (e.g., `NativeModules`, platform-specific APIs). If components don't render in web mode, document this and rely on native tests for those specific components.

### Bare React Native Projects

Bare React Native projects (no Expo) cannot easily run in web mode. Use build verification and tests instead.

```bash
# Android debug build
npx react-native build-android --mode=debug

# iOS build (macOS only)
npx react-native build-ios --mode=debug

# Run tests
npm test
```

### Static Analysis (Always Run)

```bash
# TypeScript type checking
npx tsc --noEmit

# Lint
npm run lint 2>/dev/null || npx eslint . 2>/dev/null || true

# Run test suite
npm test
```

### Document Findings (MANDATORY)

```
REACT NATIVE VALIDATION:
- Static Analysis: PASS/FAIL
  - TypeScript: PASS/FAIL
  - Lint: PASS/FAIL
  - Tests: X/Y passing
- Build Verification: PASS/FAIL/SKIPPED
  - Target: [android/ios/web]
  - Build errors: [list or "None"]
- Runtime Verification (Web Mode): PASS/FAIL/SKIPPED
  - Web server started: YES/NO/N/A
  - Playwright navigate called: YES/NO
  - Playwright snapshot called: YES/NO
  - Playwright screenshot called: YES/NO
  - Screenshots captured: [count or "N/A"]
  - UI rendered correctly: PASS/FAIL/N/A
  - Interactions tested: [list or "N/A"]
  - Web-incompatible components: [list or "None"]
- Issues: [list or "None"]
```

**IMPORTANT**: For Expo projects with web support, if Playwright tools were not called,
Runtime Verification MUST be marked as INCOMPLETE, not PASS.

### Handling Common Issues

**Expo Web Not Supported:**
If the project uses `expo-dev-client` or native-only dependencies:
1. Document: "Expo web mode not available for this project"
2. Fall back to `expo build:android` or `eas build` verification
3. Rely on `npm test` results

**No Emulator Available:**
Runtime testing on actual device/emulator requires hardware or emulator setup:
1. Document: "Native runtime validation skipped - no emulator available"
2. Use build verification + unit tests as primary validation
