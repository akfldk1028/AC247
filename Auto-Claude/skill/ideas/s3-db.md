# s3-db Skill 아이디어

> 데이터베이스 마이그레이션 및 스키마 관리

## 우선순위: 높음

## 개요
DB 스키마 변경, 마이그레이션 생성/실행, 시딩 데이터 관리

## 주요 기능

### 1. 마이그레이션 관리
```bash
/s3-db migrate         # 마이그레이션 실행
/s3-db migrate:create  # 새 마이그레이션 생성
/s3-db migrate:rollback # 롤백
/s3-db migrate:status  # 상태 확인
```

### 2. 시드 데이터
```bash
/s3-db seed           # 시드 실행
/s3-db seed:create    # 새 시드 생성
```

### 3. 스키마 분석
```bash
/s3-db schema         # 현재 스키마 출력
/s3-db schema:diff    # 변경사항 비교
```

## 지원 DB
- [ ] PostgreSQL
- [ ] MySQL
- [ ] SQLite
- [ ] MongoDB

## 연동 도구
- Prisma
- TypeORM
- Alembic (Python)
- SQLAlchemy

## 구현 시 고려사항
- 환경별 설정 (dev/staging/prod)
- 롤백 안전성
- 데이터 손실 방지

## 관련 Agent
- `s3_backend_data` - 데이터 CRUD 구현
