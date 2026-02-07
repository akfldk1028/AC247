## REACT NATIVE / EXPO RUNTIME VALIDATION

For React Native and Expo projects, use web mode for browser-based validation when possible, with native build verification as fallback.

### Expo Projects (Web Mode Validation)

Expo supports web targets, enabling Puppeteer-based runtime validation.

#### Step 1: Start Expo Web Dev Server

```bash
# Start Expo in web mode on port 8081
npx expo start --web --port=8081 &

# Wait for server to be ready
sleep 10
```

#### Step 2: Navigate and Screenshot

```
Tool: mcp__puppeteer__puppeteer_navigate
Args: {"url": "http://localhost:8081"}
```

```
Tool: mcp__puppeteer__puppeteer_screenshot
Args: {"name": "expo-web-initial"}
```

#### Step 3: Verify UI Elements

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.getElementById('root') !== null"}
```

#### Step 4: Test Interactions

```
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "[data-testid=\"submit-button\"]"}
```

#### Step 5: Cleanup

```bash
kill $(lsof -ti:8081) 2>/dev/null || true
```

**Note:** Some React Native components have no web equivalent (e.g., `NativeModules`, platform-specific APIs). If components don't render in web mode, document this and rely on native tests.

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

### Document Findings

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
  - Screenshots captured: [list or "N/A"]
  - UI rendered correctly: PASS/FAIL/N/A
  - Web-incompatible components: [list or "None"]
- Issues: [list or "None"]
```

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
