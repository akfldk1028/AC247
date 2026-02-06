---
name: s3-deploy
description: |
  S3 프로젝트 프로덕션 배포 자동화. Flutter Web/APK/iOS 빌드 및 배포.
  사용 시점: (1) 배포 준비 완료 후, (2) 릴리즈 빌드 필요 시, (3) CI/CD 파이프라인에서
disable-model-invocation: true
argument-hint: "[web|android|ios|all]"
---

# S3 Deploy Skill

프로덕션 배포를 실행합니다. 테스트 통과 후 사용하세요.

## When to Use
- 테스트가 모두 통과한 후 배포할 때
- 새 버전 릴리즈 시
- CI/CD 파이프라인에서 호출할 때

## When NOT to Use
- 테스트가 실패한 상태 → `/s3-test` 먼저
- 개발 중 확인용 → `flutter run` 직접 사용
- 빌드만 필요할 때 → `/s3-build` 사용

## Quick Start
```bash
/s3-deploy web
```

## Usage

```
/s3-deploy [target]
```

### 타겟 옵션
- `web` - Flutter Web 배포 (기본값)
- `android` - Android APK/AAB 배포
- `ios` - iOS IPA 배포 (macOS 필요)
- `all` - 모든 플랫폼 빌드

## 배포 프로세스

### Web 배포

#### Step 1: 프로덕션 빌드
```bash
cd C:\DK\S3\S3\frontend
C:\DK\flutter\bin\flutter.bat build web --release
```

#### Step 2: 빌드 결과 확인
빌드 결과: `frontend/build/web/`

#### Step 3: 배포 옵션

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

#### Step 2: AAB 빌드 (Google Play용)
```bash
C:\DK\flutter\bin\flutter.bat build appbundle --release
```
결과: `frontend/build/app/outputs/bundle/release/app-release.aab`

#### Step 3: 서명 설정
`android/key.properties` 파일 필요:
```properties
storePassword=<password>
keyPassword=<password>
keyAlias=<alias>
storeFile=<path-to-keystore>
```

### iOS 배포 (macOS만 가능)

```bash
flutter build ios --release
```

## 환경 설정

### 환경별 설정 파일
```
frontend/
├── .env.development
├── .env.staging
└── .env.production
```

### 환경변수 예시
```env
API_BASE_URL=https://api.example.com
APP_NAME=S3 App
DEBUG=false
```

### 빌드 시 환경 지정
```bash
# dart-define으로 환경 지정
flutter build web --dart-define=ENVIRONMENT=production
```

## 배포 전 체크리스트

1. [ ] 테스트 통과 (`/s3-test`)
2. [ ] 린트 검사 통과
3. [ ] 버전 업데이트 (`pubspec.yaml`)
4. [ ] 환경변수 설정 확인
5. [ ] API 엔드포인트 확인
6. [ ] 에셋 최적화

## 버전 관리

### pubspec.yaml 버전 형식
```yaml
version: 1.0.0+1
# 1.0.0 = 사용자에게 보이는 버전
# +1 = 내부 빌드 번호
```

### 버전 업데이트
```bash
# 수동으로 pubspec.yaml 수정 또는
# 스크립트 사용
```

## 배포 스크립트 예시

### PowerShell (Windows)
```powershell
# scripts/deploy-web.ps1
$ErrorActionPreference = "Stop"

Write-Host "Building Flutter Web..." -ForegroundColor Cyan
Set-Location C:\DK\S3\S3\frontend
& C:\DK\flutter\bin\flutter.bat build web --release

Write-Host "Build completed!" -ForegroundColor Green
Write-Host "Output: frontend/build/web/"
```

## 관련 Skills

- `/s3-build` - 빌드만 실행
- `/s3-test` - 배포 전 테스트
- `/s3-feature` - 새 기능 개발

## 롤백

문제 발생 시:
1. 이전 버전으로 롤백
2. 에러 로그 확인
3. Auto-Claude로 수정
