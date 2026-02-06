# s3-ci Skill 아이디어

> CI/CD 파이프라인 관리

## 우선순위: 높음

## 개요
GitHub Actions, GitLab CI 파이프라인 생성 및 관리

## 주요 기능

### 1. 파이프라인 생성
```bash
/s3-ci init              # CI 설정 초기화
/s3-ci init:github       # GitHub Actions 생성
/s3-ci init:gitlab       # GitLab CI 생성
```

### 2. 워크플로우 관리
```bash
/s3-ci workflow:list     # 워크플로우 목록
/s3-ci workflow:run      # 수동 실행
/s3-ci workflow:status   # 상태 확인
```

### 3. 배포 설정
```bash
/s3-ci deploy:setup      # 배포 워크플로우 설정
/s3-ci deploy:web        # Web 배포 파이프라인
/s3-ci deploy:android    # Android 배포 파이프라인
```

## 지원 플랫폼
- [ ] GitHub Actions
- [ ] GitLab CI
- [ ] Jenkins
- [ ] CircleCI

## 생성할 워크플로우

### Flutter
```yaml
# .github/workflows/flutter.yml
- flutter pub get
- flutter analyze
- flutter test
- flutter build web/apk
```

### Backend
```yaml
# .github/workflows/backend.yml
- pip install
- pytest
- lint
- deploy
```

## 환경 변수 관리
- GitHub Secrets 설정
- 환경별 분리 (dev/staging/prod)

## 관련 Skills
- `/s3-build` - 빌드
- `/s3-test` - 테스트
- `/s3-deploy` - 배포
