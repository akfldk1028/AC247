# Edge Patterns — 코드 템플릿 모음

> 실제 `edge/src/` 코드에서 추출한 패턴. 새 코드 작성 시 이 템플릿을 따를 것.

---

## 1. New Route Template

```typescript
// edge/src/apiroutes/[name].ts
import { Hono } from 'hono';
import type { Env } from '../types';
import type { AuthVariables } from '../middleware/auth';
import { authMiddleware } from '../middleware/auth';
import { ok, error } from '../utils/response';

const app = new Hono<{ Bindings: Env; Variables: AuthVariables }>();

// Auth 필수 라우트
app.use('*', authMiddleware);

app.get('/', async (c) => {
  const user = c.get('user');

  // 1. Request parsing
  const param = c.req.param('id');
  const query = c.req.query('page') ?? '1';
  // const body = await c.req.json();  // POST only

  // 2. Validation
  // const validation = validateXxx(body);
  // if (!validation.valid) {
  //   return c.json(error(validation.code, validation.message), validation.status);
  // }

  // 3. Business logic (Supabase, R2, etc.)
  // const data = await someService(c.env, user.jwt, ...);

  // 4. Response
  return c.json(ok({ /* response data */ }), 200);
});

export default app;
```

**index.ts에 마운트:**
```typescript
import newRoute from './apiroutes/[name]';
app.route('/api/v1/[name]', newRoute);
```

---

## 2. Supabase Service Template

```typescript
// edge/src/services/supabase.ts 에 추가

// Single object 조회 (GET + eq filter)
export async function getProjectById(
  env: Env,
  projectId: string,
  jwt: string,
): Promise<Record<string, unknown> | null> {
  const res = await supabaseRequest(env, `projects?id=eq.${projectId}&select=*`, {
    jwt,
    headers: { Accept: 'application/vnd.pgrst.object+json' },
  });
  if (!res.ok) return null;
  return res.json() as Promise<Record<string, unknown>>;
}

// List 조회 (GET + pagination)
export async function listProjects(
  env: Env,
  jwt: string,
  { userId, page, limit }: { userId: string; page: number; limit: number },
): Promise<{ items: Record<string, unknown>[]; total: number }> {
  const offset = (page - 1) * limit;
  const res = await supabaseRequest(
    env,
    `projects?user_id=eq.${userId}&select=*&order=created_at.desc&offset=${offset}&limit=${limit}`,
    {
      jwt,
      headers: { Prefer: 'count=exact' },
    },
  );
  if (!res.ok) return { items: [], total: 0 };

  const total = parseInt(res.headers.get('content-range')?.split('/')[1] ?? '0', 10);
  const items = (await res.json()) as Record<string, unknown>[];
  return { items, total };
}

// INSERT (POST + return=minimal)
export async function createProject(
  env: Env,
  jwt: string,
  data: { id: string; user_id: string; name: string; description?: string },
): Promise<boolean> {
  const res = await supabaseRequest(env, 'projects', {
    method: 'POST',
    body: data,
    jwt,
    headers: { Prefer: 'return=minimal' },
  });
  return res.ok;
}

// UPDATE (PATCH + eq filter)
export async function updateProject(
  env: Env,
  jwt: string,
  projectId: string,
  data: { name?: string; description?: string },
): Promise<boolean> {
  const res = await supabaseRequest(env, `projects?id=eq.${projectId}`, {
    method: 'PATCH',
    body: data,
    jwt,
    headers: { Prefer: 'return=minimal' },
  });
  return res.ok;
}

// DELETE
export async function deleteProject(
  env: Env,
  jwt: string,
  projectId: string,
): Promise<boolean> {
  const res = await supabaseRequest(env, `projects?id=eq.${projectId}`, {
    method: 'DELETE',
    jwt,
    headers: { Prefer: 'return=minimal' },
  });
  return res.ok;
}
```

**핵심 규칙:**
- `Accept: 'application/vnd.pgrst.object+json'` → 단일 객체 반환
- `Prefer: 'count=exact'` → `content-range` 헤더로 total count
- `Prefer: 'return=minimal'` → 201/204 응답 (body 없음)
- JWT를 항상 전달 → RLS 적용

---

## 3. Auth JWKS Implementation Template

```typescript
// edge/src/middleware/auth.ts — TODO: JWKS 검증 구현

import { createMiddleware } from 'hono/factory';
import { HTTPException } from 'hono/http-exception';
import type { Env, AuthUser } from '../types';

export type AuthVariables = { user: AuthUser };

// JWKS 캐시 (Worker 인스턴스 수명 동안 유지)
let jwksCache: { keys: JsonWebKey[]; fetchedAt: number } | null = null;
const JWKS_CACHE_TTL = 3600_000; // 1시간

async function getJwks(supabaseUrl: string): Promise<JsonWebKey[]> {
  if (jwksCache && Date.now() - jwksCache.fetchedAt < JWKS_CACHE_TTL) {
    return jwksCache.keys;
  }
  const res = await fetch(
    `${supabaseUrl}/auth/v1/.well-known/jwks.json`,
  );
  const data = (await res.json()) as { keys: JsonWebKey[] };
  jwksCache = { keys: data.keys, fetchedAt: Date.now() };
  return data.keys;
}

async function verifyJwt(
  token: string,
  supabaseUrl: string,
): Promise<{ sub: string; role: string; user_metadata?: Record<string, unknown> }> {
  const keys = await getJwks(supabaseUrl);

  // JWT header → kid 추출
  const [headerB64] = token.split('.');
  const header = JSON.parse(atob(headerB64));

  // Matching key 찾기
  const key = keys.find((k) => k.kid === header.kid);
  if (!key) throw new Error('Unknown signing key');

  // WebCrypto로 검증
  const cryptoKey = await crypto.subtle.importKey(
    'jwk', key, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify'],
  );

  const [, payloadB64, signatureB64] = token.split('.');
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = Uint8Array.from(atob(signatureB64.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));

  const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', cryptoKey, signature, data);
  if (!valid) throw new Error('Invalid signature');

  // Payload decode
  const payload = JSON.parse(atob(payloadB64));

  // Expiration check
  if (payload.exp && payload.exp < Date.now() / 1000) {
    throw new Error('Token expired');
  }

  return payload;
}

export const authMiddleware = createMiddleware<{
  Bindings: Env; Variables: AuthVariables;
}>(async (c, next) => {
  const authHeader = c.req.header('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    throw new HTTPException(401, { message: 'Authorization header required' });
  }

  const token = authHeader.slice(7);

  try {
    const payload = await verifyJwt(token, c.env.SUPABASE_URL);
    c.set('user', {
      userId: payload.sub,
      tier: (payload.user_metadata?.tier as AuthUser['tier']) ?? 'free',
      jwt: token,
    });
  } catch (err) {
    throw new HTTPException(401, { message: `Invalid token: ${(err as Error).message}` });
  }

  await next();
});
```

---

## 4. R2 Download Pattern

```typescript
// edge/src/services/r2.ts — 다운로드 추가

export async function downloadFromR2(
  r2: R2Bucket,
  key: string,
): Promise<{ data: ArrayBuffer; contentType: string } | null> {
  const object = await r2.get(key);
  if (!object) return null;

  return {
    data: await object.arrayBuffer(),
    contentType: object.httpMetadata?.contentType ?? 'application/octet-stream',
  };
}
```

---

## 5. Rate Limiting Pattern (In-Memory)

```typescript
// edge/src/middleware/rate-limit.ts
import { createMiddleware } from 'hono/factory';
import { HTTPException } from 'hono/http-exception';
import type { Env } from '../types';
import type { AuthVariables } from './auth';

const RATE_LIMITS: Record<string, { max: number; windowMs: number }> = {
  free: { max: 10, windowMs: 60_000 },
  pro: { max: 100, windowMs: 60_000 },
  enterprise: { max: 1000, windowMs: 60_000 },
};

// Note: Worker 인스턴스별 메모리 → 분산 환경에서는 Durable Objects 필요
const requestCounts = new Map<string, { count: number; resetAt: number }>();

export const rateLimitMiddleware = createMiddleware<{
  Bindings: Env; Variables: AuthVariables;
}>(async (c, next) => {
  const user = c.get('user');
  const limits = RATE_LIMITS[user.tier] ?? RATE_LIMITS.free;
  const now = Date.now();

  const entry = requestCounts.get(user.userId);
  if (!entry || now > entry.resetAt) {
    requestCounts.set(user.userId, { count: 1, resetAt: now + limits.windowMs });
  } else {
    entry.count++;
    if (entry.count > limits.max) {
      throw new HTTPException(429, { message: 'Rate limit exceeded' });
    }
  }

  await next();
});
```

---

## 6. Global Error Handler Pattern

```typescript
// edge/src/index.ts 내부
app.onError((err, c) => {
  if (err instanceof HTTPException) {
    return c.json(error(String(err.status), err.message), err.status);
  }
  console.error('Unhandled error:', err);
  return c.json(error('INTERNAL_ERROR', 'Internal server error'), 500);
});

app.notFound((c) => {
  return c.json(error('NOT_FOUND', `Route not found: ${c.req.method} ${c.req.path}`), 404);
});
```

---

## 7. File Upload Route (Complete Example)

```typescript
// edge/src/apiroutes/upload.ts — 실제 구현 참조
app.post('/', async (c) => {
  const user = c.get('user');

  // 1. Parse multipart form
  const formData = await c.req.parseBody();
  const file = formData['file'];

  // 2. Validate
  const validation = validateUploadFile(file as File | null);
  if (!validation.valid) {
    return c.json(error(validation.code, validation.message), validation.status);
  }

  // 3. Upload to R2
  const imageId = crypto.randomUUID();
  const key = generateR2Key(user.userId, 'uploads', imageId);
  await uploadToR2(c.env.R2, key, (file as File).stream(), (file as File).type);
  const imageUrl = getR2PublicUrl(c.env, key);

  // 4. Return
  return c.json(ok({
    image_id: imageId,
    image_url: imageUrl,
    size_bytes: (file as File).size,
    content_type: (file as File).type,
  }), 200);
});
```

---

## 8. Segment Route (Complete Example — 비동기 패턴)

```typescript
// edge/src/apiroutes/segment.ts — 실제 구현 참조
app.post('/', async (c) => {
  const user = c.get('user');

  // 1. Validate
  const body = await c.req.json();
  const validation = validateSegmentRequest(body);
  if (!validation.valid) return c.json(error(validation.code, validation.message), validation.status);

  // 2. Check credits
  const userInfo = await getUserCredits(c.env, user.userId, user.jwt);
  if (!userInfo || userInfo.credits <= 0) {
    return c.json(error('INSUFFICIENT_CREDITS', 'Not enough credits'), 402);
  }

  // 3. Create task (status: pending)
  const taskId = crypto.randomUUID();
  const created = await createSegmentationResult(c.env, user.jwt, {
    id: taskId,
    user_id: user.userId,
    project_id: body.project_id,
    source_image_url: body.image_url,
    text_prompt: body.text_prompt,
  });
  if (!created) return c.json(error('INTERNAL_ERROR', 'Failed to create task'), 500);

  // 4. Async backend call (don't wait for response)
  c.executionCtx.waitUntil(
    proxyToBackend(c.env, '/api/v1/predict', {
      image_url: body.image_url,
      text_prompt: body.text_prompt,
      user_id: user.userId,
      task_id: taskId,
    }),
  );

  // 5. Return immediately with 202
  return c.json(ok({ task_id: taskId, status: 'pending' }), 202);
});
```

---

## 9. Validation Template

```typescript
// edge/src/utils/validation.ts 에 추가

export function validateCreateProject(body: {
  name?: string;
  description?: string;
}): ValidationResult {
  if (!body.name || body.name.trim().length === 0) {
    return { valid: false, code: 'INVALID_REQUEST', message: 'name is required', status: 400 };
  }
  if (body.name.length > 100) {
    return { valid: false, code: 'INVALID_REQUEST', message: 'name must be 100 characters or less', status: 400 };
  }
  return { valid: true };
}
```
