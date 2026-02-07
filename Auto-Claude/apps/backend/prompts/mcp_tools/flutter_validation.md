## FLUTTER RUNTIME VALIDATION

For Flutter projects, use a combination of static analysis, build verification, and browser-based runtime validation (for web targets).

### Static Analysis (Always Run)

```bash
# Run Flutter analyzer for lint/type errors
flutter analyze

# Run unit/widget tests
flutter test
```

Document results:
```
FLUTTER STATIC ANALYSIS:
- flutter analyze: PASS/FAIL (N issues)
- flutter test: PASS/FAIL (X/Y tests passing)
```

### Web Runtime Validation (If `web/` directory exists)

When the project has a `web/` directory, launch the Flutter web dev server and use Puppeteer MCP for visual verification.

#### Step 1: Start Flutter Web Dev Server

```bash
# Start Flutter web on port 8080 in the background
flutter run -d chrome --web-port=8080 &

# Wait for server to be ready (check for "is being served at" in output)
sleep 15
```

#### Step 2: Navigate and Screenshot

```
Tool: mcp__puppeteer__puppeteer_navigate
Args: {"url": "http://localhost:8080"}
```

```
Tool: mcp__puppeteer__puppeteer_screenshot
Args: {"name": "flutter-web-initial"}
```

#### Step 3: Verify Key UI Elements

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('flt-glass-pane') !== null || document.querySelector('flutter-view') !== null"}
```

Check that the Flutter web app rendered successfully (Flutter uses `flt-glass-pane` or `flutter-view` as the root element).

#### Step 4: Test Interactions

Flutter web uses a canvas or HTML renderer. For HTML renderer, standard selectors work:

```
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "[data-testid=\"submit-button\"]"}
```

For canvas renderer, use coordinate-based clicks or evaluate Dart-side test hooks.

#### Step 5: Cleanup

```bash
# Stop the Flutter dev server
kill $(lsof -ti:8080) 2>/dev/null || true
```

### Native-Only Validation (No `web/` directory)

When the project does NOT have a `web/` directory, runtime browser validation is not possible. Instead:

```bash
# Verify APK builds successfully (Android)
flutter build apk --debug

# Or verify iOS builds (macOS only)
flutter build ios --no-codesign

# Run all tests with coverage
flutter test --coverage
```

### Document Findings

```
FLUTTER VALIDATION:
- Static Analysis: PASS/FAIL
  - Analyzer issues: [count or "None"]
  - Test results: X/Y passing
- Build Verification: PASS/FAIL
  - Target: [web/apk/ios]
  - Build errors: [list or "None"]
- Runtime Verification: PASS/FAIL/SKIPPED
  - Web server started: YES/NO/N/A
  - Screenshots captured: [list or "N/A"]
  - UI rendered correctly: PASS/FAIL/N/A
  - Interactions working: PASS/FAIL/N/A
- Issues: [list or "None"]
```

### Handling Common Issues

**Flutter SDK Not Installed:**
1. Document: "Flutter validation skipped - SDK not found"
2. Fall back to Dart static analysis: `dart analyze`
3. Add to QA report as "Manual verification required"

**Web Renderer Issues:**
Flutter web may use CanvasKit (default) or HTML renderer. If Puppeteer can't interact with canvas elements, note: "Canvas renderer - limited browser automation" and rely on `flutter test` results.
