## UNITY RUNTIME VALIDATION

For Unity projects, use batch mode CLI commands for build verification and test execution.

### EditMode Tests

```bash
# Run EditMode tests (unit tests, editor scripts)
Unity -batchmode -nographics -projectPath . \
  -runTests -testPlatform EditMode \
  -testResults test-results-editmode.xml \
  -logFile test-editmode.log
```

Parse results:
```bash
# Check test results XML
grep -c 'result="Passed"' test-results-editmode.xml
grep -c 'result="Failed"' test-results-editmode.xml
```

### PlayMode Tests

```bash
# Run PlayMode tests (runtime behavior, MonoBehaviour tests)
Unity -batchmode -nographics -projectPath . \
  -runTests -testPlatform PlayMode \
  -testResults test-results-playmode.xml \
  -logFile test-playmode.log
```

Parse results:
```bash
grep -c 'result="Passed"' test-results-playmode.xml
grep -c 'result="Failed"' test-results-playmode.xml
```

### Build Verification

```bash
# Batch build (requires BuildScript.Build method in Assets/Editor/)
Unity -batchmode -nographics -projectPath . \
  -executeMethod BuildScript.Build \
  -quit -logFile build.log
```

Check build output:
```bash
# Verify build completed without errors
grep -i "error" build.log | grep -v "0 error"
echo "Build exit code: $?"
```

### Fallback (Unity CLI Not Available)

If the Unity editor CLI is not installed or not in PATH:

```bash
# Check for .sln file and try dotnet build
dotnet build *.sln 2>&1 || echo "No .sln found or dotnet not available"

# Verify C# syntax by checking for compilation errors
find Assets -name "*.cs" -exec grep -l "class " {} \; | head -20
```

### Document Findings

```
UNITY VALIDATION:
- EditMode Tests: PASS/FAIL/SKIPPED
  - Passed: [count]
  - Failed: [count]
  - Errors: [list or "None"]
- PlayMode Tests: PASS/FAIL/SKIPPED
  - Passed: [count]
  - Failed: [count]
  - Errors: [list or "None"]
- Build Verification: PASS/FAIL/SKIPPED
  - Build target: [StandaloneWindows64/Android/WebGL/etc.]
  - Build errors: [list or "None"]
  - Build log: [summary of warnings]
- Issues: [list or "None"]
```

### Handling Common Issues

**Unity CLI Not Found:**
1. Document: "Unity batch mode validation skipped - Unity CLI not in PATH"
2. Fall back to `dotnet build` or C# syntax checks
3. Add to QA report as "Manual verification required"

**Test Framework Not Set Up:**
If the project has no test assemblies (no `Tests/` folder or `*.Tests.asmdef`):
1. Document: "No Unity test assemblies found"
2. Rely on build verification only
3. Recommend test setup for future iterations

**License Issues:**
Unity batch mode requires a valid license. If license activation fails:
1. Document: "Unity license not activated for batch mode"
2. Fall back to `dotnet build` or manual verification
