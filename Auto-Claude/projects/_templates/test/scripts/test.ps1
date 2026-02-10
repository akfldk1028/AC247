# {PROJECT_NAME} Test Script
# Usage: .\test.ps1 [scope]
# Scopes: all, unit, widget, integration, [feature_name]

param(
    [string]$Scope = "all"
)

$ErrorActionPreference = "Stop"
$FrontendPath = "{PROJECT_DIR}"
$FlutterPath = "{FLUTTER_CMD}"

function Write-Step($message) {
    Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host $message -ForegroundColor Green
}

function Write-Error($message) {
    Write-Host $message -ForegroundColor Red
}

# Navigate to frontend
Set-Location $FrontendPath

switch ($Scope) {
    "all" {
        Write-Step "Running all tests..."
        & $FlutterPath test
    }
    "unit" {
        Write-Step "Running unit tests..."
        & $FlutterPath test test/unit/
    }
    "widget" {
        Write-Step "Running widget tests..."
        & $FlutterPath test test/widgets/
    }
    "integration" {
        Write-Step "Running integration tests..."
        & $FlutterPath test integration_test/
    }
    "coverage" {
        Write-Step "Running tests with coverage..."
        & $FlutterPath test --coverage
        Write-Success "Coverage report: $FrontendPath\coverage\"
    }
    default {
        # Assume it's a feature name
        $featureTestPath = "test/features/$Scope/"
        if (Test-Path $featureTestPath) {
            Write-Step "Running tests for feature: $Scope"
            & $FlutterPath test $featureTestPath
        } else {
            Write-Error "Unknown scope or feature: $Scope"
            Write-Host "Available scopes: all, unit, widget, integration, coverage"
            Write-Host "Or specify a feature name"
            exit 1
        }
    }
}

Write-Success "Tests completed!"
