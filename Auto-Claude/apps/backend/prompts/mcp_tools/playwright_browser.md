## PLAYWRIGHT BROWSER VALIDATION

For web frontend applications, Playwright MCP tools provide browser automation and validation with cross-browser support.

### Setup

```bash
claude mcp add playwright -- npx @anthropic/mcp-playwright
```

### Available Tools

| Tool | Purpose |
|------|---------|
| `mcp__playwright__browser_navigate` | Navigate to a URL |
| `mcp__playwright__browser_screenshot` | Take a screenshot of the current page |
| `mcp__playwright__browser_click` | Click an element by selector or text |
| `mcp__playwright__browser_fill` | Fill an input field with text |
| `mcp__playwright__browser_select` | Select an option from a dropdown |
| `mcp__playwright__browser_hover` | Hover over an element |
| `mcp__playwright__browser_evaluate` | Execute JavaScript in the page context |
| `mcp__playwright__browser_snapshot` | Get the accessibility tree of the page |

### Validation Flow

#### Step 1: Navigate to Page

```
Tool: mcp__playwright__browser_navigate
Args: {"url": "http://localhost:3000"}
```

Navigate to the development server URL.

#### Step 2: Take Screenshot

```
Tool: mcp__playwright__browser_screenshot
```

Capture the current page state for visual verification.

#### Step 3: Get Accessibility Snapshot

```
Tool: mcp__playwright__browser_snapshot
```

Get the accessibility tree to verify page structure and element presence without relying on CSS selectors.

#### Step 4: Verify Elements and Interactions

**Click by text (preferred):**
```
Tool: mcp__playwright__browser_click
Args: {"element": "Submit", "ref": "s1e5"}
```

**Fill form fields:**
```
Tool: mcp__playwright__browser_fill
Args: {"element": "Email input", "ref": "s1e3", "value": "test@example.com"}
```

**Execute JavaScript for console error checking:**
```
Tool: mcp__playwright__browser_evaluate
Args: {"script": "JSON.stringify(window.__consoleErrors || [])"}
```

#### Step 5: Set Up Console Error Capture

Before testing interactions, inject error capture:
```
Tool: mcp__playwright__browser_evaluate
Args: {
  "script": "window.__consoleErrors = []; const origError = console.error; console.error = (...args) => { window.__consoleErrors.push(args.map(String)); origError.apply(console, args); };"
}
```

### Playwright vs Puppeteer

| Feature | Playwright | Puppeteer |
|---------|-----------|-----------|
| Accessibility tree | Built-in `browser_snapshot` | Not available |
| Element targeting | By `ref` from snapshot | CSS selectors only |
| Cross-browser | Chromium, Firefox, WebKit | Chromium only |
| Recommended for | New projects, complex UIs | Legacy, simple checks |

### Document Findings

```
BROWSER VERIFICATION (Playwright):
- [Page/Component]: PASS/FAIL
  - Console errors: [list or "None"]
  - Accessibility: PASS/FAIL
  - Visual check: PASS/FAIL
  - Interactions: PASS/FAIL
```
