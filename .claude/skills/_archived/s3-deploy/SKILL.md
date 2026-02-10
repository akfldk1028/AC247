---
name: s3-deploy
description: |
  S3 ?�로?�트 ?�로?�션 배포 ?�동?? Flutter Web/APK/iOS 빌드 �?배포.
  ?�용 ?�점: (1) 배포 준�??�료 ?? (2) 릴리�?빌드 ?�요 ?? (3) CI/CD ?�이?�라?�에??
disable-model-invocation: true
argument-hint: "[web|android|ios|all]"
---

# S3 Deploy Skill

?�로?�션 배포�??�행?�니?? ?�스???�과 ???�용?�세??

## When to Use
- ?�스?��? 모두 ?�과????배포????
- ??버전 릴리�???
- CI/CD ?�이?�라?�에???�출????

## When NOT to Use
- ?�스?��? ?�패???�태 ??`/s3-test` 먼�?
- 개발 �??�인????`flutter run` 직접 ?�용
- 빌드�??�요??????`/s3-build` ?�용

## Quick Start
```bash
/s3-deploy web
```

## Usage

```
/s3-deploy [target]
```

### ?��??�션
- `web` - Flutter Web 배포 (기본�?
- `android` - Android APK/AAB 배포
- `ios` - iOS IPA 배포 (macOS ?�요)
- `all` - 모든 ?�랫??빌드

## 배포 ?�로?�스

### Web 배포

#### Step 1: ?�로?�션 빌드
```bash
cd C:\DK\S3\frontend
C:\DK\flutter\bin\flutter.bat build web --release
```

#### Step 2: 빌드 결과 ?�인
빌드 결과: `frontend/build/web/`

#### Step 3: 배포 ?�션

**Firebase Hosting:**
```bash
firebase deploy --only hosting
```

**Vercel:**
```bash
vercel --prod
```

**Netlify:**
```bash
netlify deploy --prod --dir=build/web
```

**GitHub Pages:**
```bash
# gh-pages 브랜치에 배포
```

### Android 배포

#### Step 1: APK 빌드
```bash
C:\DK\flutter\bin\flutter.bat build apk --release
```
결과: `frontend/build/app/outputs/flutter-apk/app-release.apk`

#### Step 2: AAB 빌드 (Google Play??
```bash
C:\DK\flutter\bin\flutter.bat build appbundle --release
```
결과: `frontend/build/app/outputs/bundle/release/app-release.aab`

#### Step 3: ?�명 ?�정
`android/key.properties` ?�일 ?�요:
```properties
storePassword=<password>
keyPassword=<password>
keyAlias=<alias>
storeFile=<path-to-keystore>
```

### iOS 배포 (macOS�?가??

```bash
flutter build ios --release
```

## ?�경 ?�정

### ?�경�??�정 ?�일
```
frontend/
?��??� .env.development
?��??� .env.staging
?��??� .env.production
```

### ?�경변???�시
```env
API_BASE_URL=https://api.example.com
APP_NAME=S3 App
DEBUG=false
```

### 빌드 ???�경 지??
```bash
# dart-define?�로 ?�경 지??
flutter build web --dart-define=ENVIRONMENT=production
```

## 배포 ??체크리스??

1. [ ] ?�스???�과 (`/s3-test`)
2. [ ] 린트 검???�과
3. [ ] 버전 ?�데?�트 (`pubspec.yaml`)
4. [ ] ?�경변???�정 ?�인
5. [ ] API ?�드?�인???�인
6. [ ] ?�셋 최적??

## 버전 관�?

### pubspec.yaml 버전 ?�식
```yaml
version: 1.0.0+1
# 1.0.0 = ?�용?�에�?보이??버전
# +1 = ?��? 빌드 번호
```

### 버전 ?�데?�트
```bash
# ?�동?�로 pubspec.yaml ?�정 ?�는
# ?�크립트 ?�용
```

## 배포 ?�크립트 ?�시

### PowerShell (Windows)
```powershell
# scripts/deploy-web.ps1
$ErrorActionPreference = "Stop"

Write-Host "Building Flutter Web..." -ForegroundColor Cyan
Set-Location C:\DK\S3\frontend
& C:\DK\flutter\bin\flutter.bat build web --release

Write-Host "Build completed!" -ForegroundColor Green
Write-Host "Output: frontend/build/web/"
```

## 관??Skills

- `/s3-build` - 빌드�??�행
- `/s3-test` - 배포 ???�스??
- `/s3-feature` - ??기능 개발

## 롤백

문제 발생 ??
1. ?�전 버전?�로 롤백
2. ?�러 로그 ?�인
3. Auto-Claude�??�정
