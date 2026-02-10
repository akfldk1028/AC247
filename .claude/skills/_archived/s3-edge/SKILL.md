---
name: s3-edge
description: |
  Edge API (Hono + CF Workers) 개발. 새 라우트 추가, Supabase CRUD, R2 업로드, Auth JWT 검증.
  사용 시점: (1) 새 API 엔드포인트 추가 시, (2) Supabase 서비스 함수 추가 시, (3) Auth 미들웨어 수정 시
  사용 금지: Frontend UI 작업, Backend 추론 로직, Supabase 마이그레이션
argument-hint: "[route|service|auth|proxy] [description]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# s3-edge — Edge API 개발 가이드

> Edge = Full API. Flutter가 호출하는 유일한 API 서버.
> Auth, CRUD, R2, Supabase 연동, Backend 추론 프록시 담당.

## When to Use

- 새 API 엔드포인트 추가 (라우트 파일 + index.ts 마운트)
- Supabase REST 서비스 함수 추가/수정
- R2 업로드/다운로드 로직 수정
- Auth JWT 미들웨어 수정 (JWKS 검증 구현)
- Backend 프록시 로직 수정
- Response 포맷 변경
- Validation 로직 추가

## When NOT to Use

- Frontend UI 작업 → Flutter 직접 수정
- Backend SAM3 추론 로직 → `/s3-backend`
- DB 마이그레이션, RLS 정책 → `/s3-supabase`
- 모델 스크립트/노트북 → `ai/` 디렉토리

---

## Project Structure

```
edge/src/
├── index.ts                 ← Main Hono app, route mount, global middleware
├── types/
│   └── index.ts             ← Env, AuthUser, ApiResponse, TaskStatus
├── middleware/
│   └── auth.ts              ← Auth middleware (JWT verification)
├── services/
│   ├── supabase.ts          ← Supabase REST API client
│   ├── r2.ts                ← R2 upload/download helpers
│   └── vastai.ts            ← Backend proxy
├── apiroutes/
│   ├── upload.ts            ← POST /api/v1/upload
│   ├── segment.ts           ← POST /api/v1/segment
│   └── results.ts           ← GET /tasks/:id, /results, /results/:id
└── utils/
    ├── response.ts          ← ok(data), error(code, msg)
    └── validation.ts        ← File & request validation
```

**Config**: `edge/wrangler.jsonc` — R2 bucket binding `s3-images`, main: `src/index.ts`

---

## Core Patterns

### 1. Type System

```typescript
// types/index.ts
export type Env = {
  VASTAI_BACKEND_URL: string;
  API_SECRET_KEY: string;
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
  R2: R2Bucket;  // Cloudflare R2 binding
};

export type AuthUser = {
  userId: string;
  tier: 'free' | 'pro' | 'enterprise';
  jwt: string;  // Raw JWT — Supabase REST API 호출에 사용
};

export type ApiResponse<T> = {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
  meta: { request_id: string; timestamp: string };
};
```

### 2. Route Pattern (독립 Hono 인스턴스)

각 라우트 = 독립 Hono 인스턴스 → `index.ts`에서 `app.route()` 마운트.

```typescript
// apiroutes/my-route.ts
import { Hono } from 'hono';
import type { Env, AuthVariables } from '../types';
import { authMiddleware } from '../middleware/auth';
import { ok, error } from '../utils/response';

const app = new Hono<{ Bindings: Env; Variables: AuthVariables }>();
app.use('*', authMiddleware);

app.post('/', async (c) => {
  const user = c.get('user');  // AuthUser { userId, tier, jwt }
  // ... 로직
  return c.json(ok({ ... }), 200);
});

export default app;
```

```typescript
// index.ts — 마운트
app.route('/api/v1/my-route', myRoute);
```

### 3. Auth Middleware

```typescript
// middleware/auth.ts
export const authMiddleware = createMiddleware<{
  Bindings: Env; Variables: AuthVariables;
}>(async (c, next) => {
  const authHeader = c.req.header('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    throw new HTTPException(401, { message: 'Authorization header required' });
  }
  const token = authHeader.slice(7);
  // TODO: Real JWKS verification
  c.set('user', { userId: 'dev-user-id', tier: 'free', jwt: token });
  await next();
});
```

### 4. Supabase REST Helper

JWT를 그대로 전달해서 RLS가 적용되도록 함.

```typescript
// services/supabase.ts
async function supabaseRequest(env: Env, path: string, options: {
  method?: string; body?: unknown; jwt?: string; headers?: Record<string, string>;
} = {}): Promise<Response> {
  const { method = 'GET', body, jwt, headers = {} } = options;
  return fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      apikey: env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${jwt ?? env.SUPABASE_ANON_KEY}`,
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}
```

**주요 서비스 함수들:**
- `getUserCredits(env, userId, jwt)` — 크레딧 조회 (단일 객체)
- `createSegmentationResult(env, jwt, data)` — INSERT (status: pending)
- `getSegmentationResult(env, resultId, jwt)` — 단일 결과 조회
- `listSegmentationResults(env, jwt, { userId, projectId?, page, limit })` — 페이징
- `logUsage(env, jwt, { user_id, action, credits_used })` — 사용 로그

### 5. R2 Operations

```typescript
// services/r2.ts
export async function uploadToR2(
  r2: R2Bucket, key: string, data: ReadableStream | ArrayBuffer, contentType: string
): Promise<void> {
  await r2.put(key, data, { httpMetadata: { contentType } });
}

export function generateR2Key(userId: string, type: 'uploads' | 'masks', id: string): string {
  return `${type}/${userId}/${id}`;
}
```

### 6. Response Helpers

```typescript
// utils/response.ts
export function ok<T>(data: T): ApiResponse<T>     // success: true
export function error(code: string, message: string): ApiResponse<null>  // success: false
```

**사용법:**
```typescript
return c.json(ok({ image_id, image_url }), 200);
return c.json(error('INVALID_REQUEST', 'File is required'), 400);
return c.json(error('NOT_FOUND', 'Task not found'), 404);
```

### 7. Backend Proxy (비동기)

```typescript
// services/vastai.ts
export async function proxyToBackend(env: Env, path: string, body: Record<string, unknown>): Promise<Response> {
  return fetch(`${env.VASTAI_BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': env.API_SECRET_KEY },
    body: JSON.stringify(body),
  });
}
```

**사용법 (비동기, 응답 대기 안함):**
```typescript
c.executionCtx.waitUntil(
  proxyToBackend(c.env, '/api/v1/predict', { image_url, text_prompt, user_id, task_id })
);
return c.json(ok({ task_id, status: 'pending' }), 202);
```

### 8. Validation

```typescript
// utils/validation.ts
export type ValidationResult =
  | { valid: true }
  | { valid: false; code: string; message: string; status: number };

export const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
export const MAX_FILE_SIZE = 10 * 1024 * 1024;  // 10MB

export function validateUploadFile(file: File | null): ValidationResult
export function validateSegmentRequest(body: { image_url?, text_prompt? }): ValidationResult
```

---

## Commands

| Command | Description |
|---------|-------------|
| `npx wrangler dev` | 로컬 개발 서버 (`edge/` 디렉토리에서) |
| `npx tsc --noEmit` | 타입 체크 |
| `npx wrangler deploy` | Cloudflare Workers 배포 |

---

## Checklist: 새 라우트 추가

1. `edge/src/apiroutes/[name].ts` — 독립 Hono 인스턴스 생성
2. `edge/src/index.ts` — `app.route()` 마운트 추가
3. `edge/src/services/supabase.ts` — 필요한 서비스 함수 추가
4. `edge/src/utils/validation.ts` — 필요한 검증 함수 추가
5. `edge/src/types/index.ts` — 필요한 타입 추가
6. `docs/contracts/api-contracts.md` — **API Contract SSoT 먼저 수정**
7. `npx tsc --noEmit` — 타입 체크 통과 확인

---

## Related Skills

- `/s3-backend` — Backend SAM3 추론 (Edge에서 프록시하는 대상)
- `/s3-supabase` — DB 스키마, RLS (Edge가 CRUD하는 대상)
- `/s3-build` — 전체 빌드 검증
- `/s3-test` — 전체 테스트 실행

---

## References

- [edge-patterns.md](references/edge-patterns.md) — 코드 템플릿 모음
- [API Contract SSoT](C:\DK\S3\docs\contracts\api-contracts.md) — 엔드포인트 명세
- [Edge README](C:\DK\S3\edge\README.md) — Agent 작업 가이드
