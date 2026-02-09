## WEB BROWSER VALIDATION (Playwright MCP) — MANDATORY

### Pre-Validation: Automatic Browser Validator

**Before you begin Phase 4**, the `BrowserValidator` has already run automatically as part of
the QA validator pipeline. It uses Python `playwright` (headless Chromium) to:

1. Auto-start the dev server from `project_index.json` config
2. Poll the port until ready (120s timeout)
3. Navigate to `localhost:PORT` (networkidle → fallback domcontentloaded)
4. Take a screenshot → saved to `spec_dir/screenshots/01-initial-load.png`
5. Capture accessibility tree snapshot (node count + role distribution)
6. Collect all console errors/warnings
7. Kill the dev server and clean up

The results are injected into your prompt as `ValidatorResult`. Check the **Browser Validation**
section in the validator results above — if it shows screenshots, a11y summary, and console status,
**you already have baseline evidence**. Your job is to go deeper: test interactions, verify
multi-page navigation, and validate against the spec acceptance criteria.

If the auto-validator was skipped (playwright not installed, no dev server config), you MUST
perform the full manual flow below.

---

**CRITICAL REQUIREMENT**: For ANY project with a web UI (web frontend, Flutter web, Expo web, Tauri),
you MUST use the Playwright MCP tools listed below for browser verification.
**`curl`, `wget`, or raw HTTP requests do NOT count as browser verification.**

You MUST call at minimum these 3 tools during browser verification:
1. `mcp__playwright__browser_navigate` — Navigate to the app URL
2. `mcp__playwright__browser_snapshot` — Get accessibility tree
3. `mcp__playwright__browser_take_screenshot` — Capture visual state

If you skip these tools and only use `curl` or code review, your QA review is INVALID.

Playwright uses **accessibility snapshots** to identify elements instead of CSS selectors — this works
with canvas-based renderers (Flutter CanvasKit, Unity WebGL) as well as standard HTML.

### Dev Server Prerequisite (MANDATORY)

Before browser validation, you MUST start the dev server.
Refer to the **DEV SERVER CONFIGURATION** section (injected above in the prompt) for:
- The correct `dev_command` to start the server
- The `port` and `URL` to navigate to
- Cross-platform port health check commands (Windows PowerShell / Linux bash)
- Cross-platform server cleanup commands

**Never hardcode ports or use fixed sleep durations** — always use the values from DEV SERVER CONFIGURATION.
If no DEV SERVER CONFIGURATION is provided, check `project_index.json` for `dev_command` and `default_port`.

### Available Tools

| Tool | Purpose | REQUIRED? |
|------|---------|-----------|
| `mcp__playwright__browser_navigate` | Navigate to URL | **YES — MUST CALL** |
| `mcp__playwright__browser_snapshot` | Get accessibility tree snapshot (element discovery) | **YES — MUST CALL** |
| `mcp__playwright__browser_take_screenshot` | Capture screenshot for visual verification | **YES — MUST CALL** |
| `mcp__playwright__browser_click` | Click element (by ref from snapshot) | Yes, for interactive apps |
| `mcp__playwright__browser_type` | Type text into input field | Yes, for apps with inputs |
| `mcp__playwright__browser_select_option` | Select dropdown option | As needed |
| `mcp__playwright__browser_hover` | Hover over element | As needed |
| `mcp__playwright__browser_press_key` | Press keyboard key (Enter, Tab, etc.) | As needed |
| `mcp__playwright__browser_console_messages` | Read browser console output | **YES — MUST CALL** |
| `mcp__playwright__browser_wait_for` | Wait for text or element to appear | As needed |
| `mcp__playwright__browser_tab_list` | List open browser tabs | As needed |
| `mcp__playwright__browser_tab_new` | Open new tab | As needed |
| `mcp__playwright__browser_tab_select` | Switch to tab | As needed |
| `mcp__playwright__browser_resize` | Resize browser viewport | As needed |
| `mcp__playwright__browser_close` | Close browser | As needed |

### Validation Flow (MANDATORY — Follow All Steps)

#### Step 1: Navigate to Page (MUST CALL)

```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:PORT"}
```

Navigate to the development server URL from DEV SERVER CONFIGURATION.

#### Step 2: Take Accessibility Snapshot (MUST CALL)

```
Tool: mcp__playwright__browser_snapshot
```

Returns the **accessibility tree** of the page. Each element has a `ref` identifier
you MUST use for click/type/hover actions. This is the primary method for discovering
interactive elements — prefer it over CSS selectors.

Example output:
```
- button "Submit" [ref=e1]
- textbox "Email" [ref=e2]
- heading "Welcome" [ref=e3]
```

#### Step 3: Take Screenshot and SAVE to Disk (MUST CALL)

```
Tool: mcp__playwright__browser_take_screenshot
```

Capture the page state for visual verification. Compare against spec requirements
to confirm the UI matches the intended design.

**MANDATORY: Save screenshots to spec directory for audit trail.**

After taking a screenshot, you MUST save it to `screenshots/` in the spec directory:

```bash
# Create screenshots directory if it doesn't exist
mkdir -p .auto-claude/specs/CURRENT_SPEC/screenshots

# The screenshot is returned inline by Playwright.
# Save a record of what was verified in the QA report.
```

**Screenshot naming convention:**
- `01-initial-load.png` — First page load
- `02-page-{name}.png` — Each page/route visited
- `03-after-{action}.png` — After significant interactions
- `99-final-state.png` — Final state before cleanup

Playwright MCP `browser_take_screenshot` can accept a `fileName` argument to save to disk:
```
Tool: mcp__playwright__browser_take_screenshot
Args: {"fileName": "screenshots/01-initial-load"}
```

If `fileName` is not supported, use Bash to note the screenshot was captured:
```bash
echo "Screenshot captured: [description] at $(date -Iseconds)" >> .auto-claude/specs/CURRENT_SPEC/screenshots/manifest.txt
```

#### Step 4: Test Interactions (MUST DO for interactive apps)

**Click buttons/links (using ref from snapshot):**
```
Tool: mcp__playwright__browser_click
Args: {"element": "Submit button", "ref": "e1"}
```

**Type into input fields:**
```
Tool: mcp__playwright__browser_type
Args: {"element": "Email input", "ref": "e2", "text": "test@example.com"}
```

**Select dropdown options:**
```
Tool: mcp__playwright__browser_select_option
Args: {"element": "Country select", "ref": "e5", "values": ["US"]}
```

**Press keyboard keys:**
```
Tool: mcp__playwright__browser_press_key
Args: {"key": "Enter"}
```

After each significant interaction, call `browser_snapshot` or `browser_take_screenshot`
to verify the UI updated correctly.

#### Step 5: Check Console for Errors (MUST CALL)

```
Tool: mcp__playwright__browser_console_messages
```

Returns all console messages (log, warn, error) from the browser. Check for
JavaScript errors, unhandled promise rejections, or framework warnings.

#### Step 6: Wait for Async Content (As Needed)

```
Tool: mcp__playwright__browser_wait_for
Args: {"text": "Loading complete"}
```

Wait for specific text to appear on the page. Useful after navigation or
async operations (API calls, animations).

### Document Findings (MANDATORY)

```
BROWSER VERIFICATION:
- Playwright tools used: [list of mcp__playwright__ tools called]
- [Page/Component]: PASS/FAIL
  - Console errors: [list or "None"]
  - Visual check: PASS/FAIL (screenshot captured)
  - Accessibility snapshot: [key elements found]
  - Interactions tested: [list]
  - Interactions result: PASS/FAIL
```

**If "Playwright tools used" is empty or only contains navigate, your review is INCOMPLETE.**

### Element Discovery Strategy

Playwright MCP uses accessibility snapshots instead of CSS selectors:

1. **`browser_snapshot`** — Get the accessibility tree (ALWAYS start here)
2. Use `ref` values from the snapshot for all interactions
3. Element descriptions (role + name) help identify the right target
4. If elements aren't in the snapshot, they may lack accessibility attributes —
   note this as an accessibility issue in the QA report

### Multi-Page Verification (MANDATORY for apps with multiple pages/routes)

For apps with more than one page, you MUST verify EACH page individually.

#### Step A: Discover All Routes/Pages

Search the codebase for route definitions:

```bash
# Flutter: Named routes, GoRouter, Navigator
grep -rn "MaterialPageRoute\|GoRoute\|routes:\|Navigator.push\|/[a-z]" lib/ --include="*.dart" | head -30

# React/Next.js: React Router, Next.js pages
grep -rn "Route path=\|<Link\|useRouter\|router\." src/ --include="*.tsx" --include="*.jsx" | head -30
# Also check: ls src/pages/ or ls app/

# Vue: Vue Router
grep -rn "path:\|component:" src/router/ --include="*.ts" --include="*.js" | head -30
```

Also read `spec.md` for the list of expected pages/screens.

#### Step B: Create Page Verification Checklist

Build a checklist of ALL pages from spec + route discovery:

```
PAGE VERIFICATION CHECKLIST:
| # | Page Name | Route/URL | Key Elements | Status |
|---|-----------|-----------|-------------|--------|
| 1 | Home      | /         | header, nav | PENDING |
| 2 | Login     | /login    | form, submit| PENDING |
| 3 | Dashboard | /dashboard| charts, data| PENDING |
```

#### Step C: Verify Each Page (MANDATORY for each page)

For EACH page in the checklist:

1. **Navigate** to the page route:
```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:PORT/route"}
```

2. **Snapshot** the accessibility tree:
```
Tool: mcp__playwright__browser_snapshot
```

3. **Screenshot** and save:
```
Tool: mcp__playwright__browser_take_screenshot
Args: {"fileName": "screenshots/02-page-{name}"}
```

4. **Check console** for page-specific errors:
```
Tool: mcp__playwright__browser_console_messages
```

5. **Test interactions** specific to this page

6. **Mark** the page as PASS/FAIL in the checklist

#### Step D: Document Multi-Page Results

```
MULTI-PAGE VERIFICATION:
- Total pages discovered: [N]
- Pages verified: [N/N]
- Pages passed: [N]
- Pages failed: [N]

| Page | Route | Screenshot | Snapshot | Interactions | Console | Result |
|------|-------|-----------|----------|-------------|---------|--------|
| Home | /     | ✅ 02-home | ✅ 5 elements | ✅ nav links | ✅ 0 errors | PASS |
| Login| /login| ✅ 03-login| ✅ form refs | ✅ submit  | ✅ 0 errors | PASS |
```

**If ANY page FAILS, the overall Browser Verification is FAIL.**

---

### Tips for Canvas-Based Apps (Flutter, Unity)

- Flutter web CanvasKit and Unity WebGL render to canvas, not DOM
- Accessibility snapshots still work if the framework exposes semantics
- For Flutter: ensure `Semantics` widgets are used in the widget tree
- **Take screenshots as the primary validation method for canvas apps**
- If the snapshot is empty, rely on screenshot + console messages
- You MUST still call `browser_navigate`, `browser_snapshot`, and `browser_take_screenshot`
  even for canvas apps — these are required regardless of renderer type
