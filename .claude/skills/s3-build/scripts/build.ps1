# S3 Build Script
# Usage: .\build.ps1 [target]
# Targets: all, flutter, web, apk, code

param(
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$FrontendPath = "C:\DK\S3\S3\frontend"
$FlutterPath = "C:\DK\flutter\bin\flutter.bat"

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

switch ($Target) {
    "code" {
        Write-Step "Running code generation (Freezed, Riverpod)..."
        dart run build_runner build --delete-conflicting-outputs
        Write-Success "Code generation complete!"
    }
    "flutter" {
        Write-Step "Getting dependencies..."
        & $FlutterPath pub get

        Write-Step "Running code generation..."
        dart run build_runner build --delete-conflicting-outputs

        Write-Success "Flutter setup complete!"
    }
    "web" {
        Write-Step "Building Flutter Web..."
        & $FlutterPath build web --release
        Write-Success "Web build complete! Output: $FrontendPath\build\web\"
    }
    "apk" {
        Write-Step "Building Android APK..."
        & $FlutterPath build apk --release
        Write-Success "APK build complete! Output: $FrontendPath\build\app\outputs\flutter-apk\"
    }
    "all" {
        Write-Step "Getting dependencies..."
        & $FlutterPath pub get

        Write-Step "Running code generation..."
        dart run build_runner build --delete-conflicting-outputs

        Write-Step "Building Flutter Web..."
        & $FlutterPath build web --release

        Write-Success "Full build complete!"
        Write-Host "`nBuild outputs:"
        Write-Host "  Web: $FrontendPath\build\web\"
    }
    default {
        Write-Error "Unknown target: $Target"
        Write-Host "Available targets: all, flutter, web, apk, code"
        exit 1
    }
}
