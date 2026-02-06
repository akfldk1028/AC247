# s3-security Skill 아이디어

> 보안 스캔 및 취약점 검사

## 우선순위: 높음

## 개요
코드 보안 분석, 의존성 취약점 검사, OWASP 체크리스트 검증

## 주요 기능

### 1. 코드 스캔
```bash
/s3-security scan         # 전체 스캔
/s3-security scan:flutter # Flutter 코드만
/s3-security scan:backend # Backend만
```

### 2. 의존성 검사
```bash
/s3-security deps         # 취약한 의존성 검사
/s3-security deps:update  # 보안 업데이트 적용
```

### 3. 설정 검사
```bash
/s3-security config       # 설정 파일 검사
/s3-security secrets      # 하드코딩된 시크릿 검색
```

## 검사 항목

### Flutter
- [ ] 하드코딩된 API 키
- [ ] 안전하지 않은 HTTP 연결
- [ ] 취약한 패키지 버전
- [ ] ProGuard/R8 설정

### Backend
- [ ] SQL Injection
- [ ] XSS
- [ ] CSRF
- [ ] 인증/인가 취약점

## 도구 연동
- Semgrep
- Snyk
- OWASP Dependency Check
- flutter pub outdated

## 출력 형식
- JSON 리포트
- HTML 대시보드
- CI 통합 가능

## 관련 Agent
- `s3_backend_auth` - 인증 보안
