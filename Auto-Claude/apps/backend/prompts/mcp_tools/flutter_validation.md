## FLUTTER RUNTIME VALIDATION

For Flutter projects, you MUST perform BOTH static analysis AND browser-based runtime validation.

**CRITICAL RULE**: Static analysis (`flutter analyze`, `flutter test`) alone is NEVER sufficient.
You MUST launch the app in Chrome and verify it with Playwright MCP tools.
Using `curl`, `wget`, or raw HTTP requests does NOT count as browser verification.

---

### PHASE A: Static Analysis (MANDATORY)

```bash
# Run Flutter analyzer for lint/type errors
flutter analyze

# Run unit/widget tests (if they exist)
flutter test
```

Document results:
```
FLUTTER STATIC ANALYSIS:
- flutter analyze: PASS/FAIL (N issues)
- flutter test: PASS/FAIL (X/Y tests passing)
```

---

### PHASE B: Browser Runtime Validation (MANDATORY — DO NOT SKIP)

> **YOU MUST COMPLETE ALL STEPS BELOW. SKIPPING ANY STEP IS A QA FAILURE.**
> If you approve a Flutter web app without calling `mcp__playwright__browser_navigate`,
> `mcp__playwright__browser_snapshot`, and `mcp__playwright__browser_take_screenshot`,
> your review is INVALID.

#### Step 0: Resolve Dependencies and Ensure Web Platform (MANDATORY)

**CRITICAL**: Before running ANY Flutter commands, you MUST resolve dependencies first.
This is especially important in worktree/isolated workspace environments.

```bash
# Step 0a: Resolve dependencies (ALWAYS run this first)
flutter pub get

# Step 0b: Ensure web platform exists
# Check if web/ directory exists. If not, create it:
flutter create --platforms web .
```

Or use `web_setup_command` from DEV SERVER CONFIGURATION if provided.

**If `flutter pub get` fails**, check if `pubspec.yaml` exists in the current directory.
If you're in a worktree, the file should be there via git checkout.

#### Step 1: Start Flutter Web Dev Server (MANDATORY)

Use the `dev_command` from **DEV SERVER CONFIGURATION** (injected above in the prompt).
If no DEV SERVER CONFIGURATION is available, use: `flutter run -d chrome --web-port=8080`

Start the server in the background:

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow -FilePath "flutter" -ArgumentList "run", "-d", "chrome", "--web-port=PORT"
```

**Linux/macOS (Bash):**
```bash
flutter run -d chrome --web-port=PORT &
```

Replace `PORT` with the actual port from DEV SERVER CONFIGURATION.

#### Step 2: Wait for Server Ready — Cross-Platform Port Polling (MANDATORY)

**Do NOT use `sleep 15` or any fixed sleep.** Poll the port until the server is listening.

Use the health check commands from DEV SERVER CONFIGURATION, or:

**Windows (PowerShell):**
```powershell
$timeout = 120; $elapsed = 0
while ($elapsed -lt $timeout) {
  try { $tcp = New-Object System.Net.Sockets.TcpClient('localhost', PORT); $tcp.Close(); break }
  catch { Start-Sleep -Seconds 3; $elapsed += 3 }
}
```

**Linux/macOS (Bash):**
```bash
timeout=120; elapsed=0
while [ $elapsed -lt $timeout ]; do
  curl -s http://localhost:PORT > /dev/null 2>&1 && break
  sleep 3; elapsed=$((elapsed + 3))
done
```

#### Step 3: Navigate to the App (MANDATORY — MUST CALL THIS TOOL)

You MUST call this Playwright tool. Do NOT substitute with curl or wget.

```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:PORT"}
```

If navigation fails, retry up to 3 times with 10-second waits between attempts.

#### Step 4: Take Accessibility Snapshot (MANDATORY — MUST CALL THIS TOOL)

You MUST call this tool to discover interactive elements on the page.

```
Tool: mcp__playwright__browser_snapshot
```

This returns the accessibility tree with `ref` identifiers for each element.
Use these `ref` values for all subsequent interactions (clicks, typing).

**If the snapshot is empty** (CanvasKit renderer without Semantics widgets):
- This is still MANDATORY to attempt
- Document: "Accessibility snapshot empty — CanvasKit renderer without Semantics"
- Proceed to screenshot and interaction testing

#### Step 5: Take Screenshot and SAVE (MANDATORY — MUST CALL THIS TOOL)

You MUST capture a screenshot and save it for audit trail.

```bash
# Create screenshots directory
mkdir -p screenshots
```

```
Tool: mcp__playwright__browser_take_screenshot
Args: {"fileName": "screenshots/01-initial-load"}
```

Compare the screenshot against spec requirements:
- Does the UI match what was specified?
- Are all expected elements visible?
- Is the layout correct?

**Save additional screenshots after interactions:**
```
Tool: mcp__playwright__browser_take_screenshot
Args: {"fileName": "screenshots/02-after-{action}"}
```

#### Step 6: Test Interactions (MANDATORY for apps with interactive elements)

You MUST test at least the core interactions specified in the acceptance criteria.

Use `ref` values from the accessibility snapshot:

```
Tool: mcp__playwright__browser_click
Args: {"element": "Button description", "ref": "e1"}
```

```
Tool: mcp__playwright__browser_type
Args: {"element": "Input description", "ref": "e2", "text": "test value"}
```

After each interaction, take a new snapshot or screenshot to verify the result:

```
Tool: mcp__playwright__browser_snapshot
```

**For calculator apps**: Test at minimum: digit input, operator, equals, clear.
**For form apps**: Test at minimum: input fields, submit button, validation.
**For list/CRUD apps**: Test at minimum: create, read, edit, delete operations.

#### Step 7: Check Console for Errors (MANDATORY — MUST CALL THIS TOOL)

```
Tool: mcp__playwright__browser_console_messages
```

Check for:
- JavaScript/Dart errors (CRITICAL)
- Flutter framework warnings
- Unhandled exceptions
- Failed network requests

#### Step 8: Cleanup (MANDATORY)

**Windows (PowerShell):**
```powershell
Get-NetTCPConnection -LocalPort PORT -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

**Linux/macOS (Bash):**
```bash
kill $(lsof -ti:PORT) 2>/dev/null || true
```

Replace `PORT` with the actual port from DEV SERVER CONFIGURATION.

---

### PHASE B2: Marionette MCP — Flutter Widget Interaction (PREFERRED for Flutter)

> **Marionette MCP provides direct widget-level interaction** — tapping buttons, entering text,
> scrolling to elements — without relying on DOM selectors or accessibility snapshots.
> This works perfectly with CanvasKit renderer where Playwright snapshots may be empty.
>
> **The browser_validator has already injected `marionette_flutter` and patched `main.dart`.**
> You do NOT need to add the package or modify code — just start the app and connect.

#### Step M1: Start Flutter App in Debug Mode

Start the app so the VM service is available (debug mode required for Marionette):

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow -FilePath "flutter" -ArgumentList "run", "-d", "web-server", "--web-port=PORT"
```

**Linux/macOS (Bash):**
```bash
flutter run -d web-server --web-port=PORT &
```

Wait for the server to be ready (see Phase B Step 2 for port polling).

Then look for the **VM service URI** in the server output:
```
The Dart VM service is listening on ws://127.0.0.1:XXXXX/YYYY=/ws
```

If the browser validator report includes `VM service URI`, use that directly.

#### Step M2: Connect to the Running App

```
Tool: mcp__marionette__connect
Args: {"vmServiceUri": "ws://127.0.0.1:XXXXX/YYYY=/ws"}
```

Use the VM service URI from the server output or validator report.

#### Step M3: Get Interactive Elements

```
Tool: mcp__marionette__get_interactive_elements
```

This returns ALL interactive widgets visible on screen — buttons, text fields, checkboxes, etc.
with their keys, text content, and widget types. Much more reliable than Playwright's a11y snapshot
for CanvasKit-rendered Flutter apps.

#### Step M4: Interact with Widgets

**Tap a button/element:**
```
Tool: mcp__marionette__tap
Args: {"text": "="}
```

**Enter text in a field:**
```
Tool: mcp__marionette__enter_text
Args: {"text": "Hello World", "key": "input_field_key"}
```

**Scroll to find elements off-screen:**
```
Tool: mcp__marionette__scroll_to
Args: {"text": "Submit"}
```

#### Step M5: Take Screenshots (After Each Interaction)

```
Tool: mcp__marionette__take_screenshots
```

Returns base64 screenshots of all active views. Save these for the QA report.

#### Step M6: Check Logs

```
Tool: mcp__marionette__get_logs
```

Check for runtime errors, exceptions, or unexpected warnings.

#### Step M7: Disconnect

```
Tool: mcp__marionette__disconnect
```

**When to use Marionette vs Playwright:**
- **Marionette**: Flutter projects (direct widget access, works with CanvasKit)
- **Playwright**: Web projects (React, Vue, Angular, etc.) or when Marionette is unavailable

If Marionette MCP is not available (tools not registered), fall back to Playwright (Phase B).

---

### PHASE C: Native-Only Validation (FALLBACK — Only if web COMPLETELY fails)

Use this ONLY if Flutter web setup fails entirely (e.g., `flutter create --platforms web .` errors out).
You MUST document WHY web validation failed before falling back.

```bash
# Verify APK builds successfully (Android)
flutter build apk --debug

# Or verify iOS builds (macOS only)
flutter build ios --no-codesign

# Run all tests with coverage
flutter test --coverage
```

---

### Document Findings (MANDATORY)

```
FLUTTER VALIDATION:
- Static Analysis: PASS/FAIL
  - Analyzer issues: [count or "None"]
  - Test results: X/Y passing
- Build Verification: PASS/FAIL
  - Target: [web/apk/ios]
  - Build errors: [list or "None"]
- Runtime Verification: PASS/FAIL
  - Web server started: YES/NO
  - Playwright navigate called: YES/NO
  - Playwright snapshot called: YES/NO
  - Playwright screenshot called: YES/NO
  - Screenshots saved to screenshots/: YES/NO
  - Screenshots captured: [count] — files: [list filenames]
  - UI matches spec: PASS/FAIL
  - Pages verified: [N/N if multi-page]
  - Interactions tested: [list of interactions]
  - Console errors: [list or "None"]
- Issues: [list or "None"]
```

**IMPORTANT**: If `Playwright navigate called` or `Playwright screenshot called` is NO,
your review MUST be marked as INCOMPLETE, not PASS.

---

### Handling Common Issues

**Flutter SDK Not Installed:**
1. Document: "Flutter validation skipped - SDK not found"
2. Fall back to Dart static analysis: `dart analyze`
3. Add to QA report as "Manual verification required"

**Web Renderer Issues:**
Flutter web uses CanvasKit (default) or WASM renderer. HTML renderer has been removed.
- CanvasKit: Accessibility snapshot may be empty if `Semantics` widgets are not used
- **Preferred**: Use Marionette MCP (Phase B2) for Flutter — direct widget interaction regardless of renderer
- If Marionette unavailable, use Playwright (Phase B) with screenshot-based verification
- In BOTH cases, you MUST still call `browser_navigate` and `browser_take_screenshot`
- If Playwright snapshot is empty, this is expected for CanvasKit — use Marionette or `flutter test` for logic
