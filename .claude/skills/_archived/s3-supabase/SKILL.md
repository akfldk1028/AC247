---
name: s3-supabase
description: |
  Supabase DB 관리. 마이그레이션, RLS 정책, Auth 트리거, Realtime, Edge Functions (Deno).
  사용 시점: (1) 새 테이블/컬럼 추가 시, (2) RLS 정책 수정 시, (3) Edge Function 개발 시
  사용 금지: Edge API 라우트, Backend 추론, Frontend UI, API 로직 구현
argument-hint: "[migration|rls|function|realtime|seed] [description]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# s3-supabase — Supabase 관리 가이드

> Supabase = DB + Auth + Realtime.
> Edge가 모든 CRUD (anon key + JWT), Backend가 UPDATE만 (service_role).

## When to Use

- 새 테이블/컬럼 추가 (마이그레이션)
- RLS 정책 수정/추가
- Auth 트리거 수정
- Realtime 구독 설정
- Edge Function 개발 (Deno)
- Seed 데이터 관리

## When NOT to Use

- Edge API 라우트/CRUD 로직 → `/s3-edge`
- Backend SAM3 추론 → `/s3-backend`
- Frontend UI → Flutter 직접
- API 비즈니스 로직 → `/s3-edge`

---

## Project Structure

```
supabase/
├── config.toml                    ← 프로젝트 설정 (PG15, Auth, Storage, Realtime)
├── seed.sql                       ← 시드 데이터 (선택사항)
├── README.md
├── migrations/
│   ├── 20260209120000_create_users_profile.sql
│   ├── 20260209120001_create_projects.sql
│   ├── 20260209120002_create_segmentation_results.sql
│   └── 20260209120003_create_usage_logs.sql
└── functions/
    ├── _shared/
    │   ├── cors.ts                ← 공유 CORS 헤더
    │   └── supabase-client.ts     ← Admin client factory
    └── process-webhook/
        └── index.ts               ← Webhook 처리 (stub)
```

---

## Database Schema (4 Tables)

| Table | PK | 핵심 필드 | RLS |
|-------|-----|----------|-----|
| `users_profile` | `id` (= auth.uid()) | tier, credits, display_name | self (id = auth.uid()) |
| `projects` | `id` (UUID) | user_id, name, description | owner (user_id = auth.uid()) |
| `segmentation_results` | `id` (UUID) | project_id, source_image_url, mask_image_url, text_prompt, status, labels, metadata | owner (user_id = auth.uid()) |
| `usage_logs` | `id` (UUID) | user_id, action, credits_used | SELECT: owner, INSERT: service_role |

**Relationships:**
```
auth.users → users_profile (1:1, trigger)
users_profile → projects (1:N, CASCADE)
projects → segmentation_results (1:N, CASCADE)
users_profile → usage_logs (1:N, CASCADE)
```

---

## Core Patterns

### 1. Migration File Naming

**형식**: `YYYYMMDDHHmmss_description.sql`

```
20260209120000_create_users_profile.sql
20260209120001_create_projects.sql
20260210150000_add_tags_to_projects.sql   ← 새 마이그레이션 예시
```

**생성 명령**: `supabase migration new [description]`

### 2. Migration Template (완전한 테이블)

```sql
-- Migration: [description]

-- ============================================================
-- Table
-- ============================================================
CREATE TABLE IF NOT EXISTS [table_name] (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,

    -- Fields
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'error')),

    -- JSON fields
    labels JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Numeric
    credits INTEGER NOT NULL DEFAULT 100,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX idx_[table]_user_id ON [table_name](user_id);
CREATE INDEX idx_[table]_created_at ON [table_name](created_at DESC);

-- ============================================================
-- Trigger: auto-update updated_at
-- ============================================================
CREATE TRIGGER [table_name]_updated_at
    BEFORE UPDATE ON [table_name]
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE [table_name] ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own [table]"
    ON [table_name] FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own [table]"
    ON [table_name] FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own [table]"
    ON [table_name] FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own [table]"
    ON [table_name] FOR DELETE
    USING (auth.uid() = user_id);
```

### 3. RLS Patterns (5가지)

#### Pattern A: Owner-Only (가장 일반적)
```sql
-- users_profile, projects, segmentation_results
CREATE POLICY "Users can view own data"
    ON [table] FOR SELECT
    USING (auth.uid() = user_id);
```

#### Pattern B: Self-Referential (users_profile)
```sql
-- id = auth.uid() (users_profile만)
CREATE POLICY "Users can view own profile"
    ON users_profile FOR SELECT
    USING (auth.uid() = id);
```

#### Pattern C: Service-Role INSERT (usage_logs)
```sql
-- 사용자는 INSERT 불가, service_role만 INSERT
CREATE POLICY "Service role can insert usage"
    ON usage_logs FOR INSERT
    WITH CHECK (true);
-- Note: anon key로는 RLS 적용됨 → auth.uid() 없으면 실패
-- service_role key → RLS bypass → INSERT 가능
```

#### Pattern D: Public Read
```sql
-- 모든 인증 사용자 읽기 가능 (사용 안 함, 참고용)
CREATE POLICY "Authenticated users can read"
    ON [table] FOR SELECT
    USING (auth.role() = 'authenticated');
```

#### Pattern E: Related Resource via FK
```sql
-- project 소유자만 결과 조회 (segmentation_results는 user_id 직접 참조)
-- 만약 user_id가 없고 FK만 있는 경우:
CREATE POLICY "Project owners can view results"
    ON segmentation_results FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = segmentation_results.project_id
            AND projects.user_id = auth.uid()
        )
    );
```

### 4. Auth Trigger (handle_new_user)

```sql
-- 20260209120000_create_users_profile.sql 에 포함

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users_profile (id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();
```

**핵심:**
- `AFTER INSERT ON auth.users` (회원가입 직후)
- `SECURITY DEFINER` — RLS bypass (users_profile INSERT 가능)
- `COALESCE` — display_name 없으면 email 사용
- defaults: `tier='free'`, `credits=100`

### 5. Realtime Setup

```sql
-- segmentation_results만 Realtime 활성화
ALTER PUBLICATION supabase_realtime ADD TABLE segmentation_results;
```

**Flutter에서 구독:**
```dart
supabase.from('segmentation_results')
    .stream(primaryKey: ['id'])
    .eq('user_id', userId)
    .listen((data) { /* 상태 변경 처리 */ });
```

### 6. updated_at Trigger Function

```sql
-- 모든 테이블이 공유하는 함수 (첫 번째 마이그레이션에서 생성)
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Edge Functions (Deno)

### Shared Utilities

```typescript
// functions/_shared/cors.ts
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-API-Key',
};
```

```typescript
// functions/_shared/supabase-client.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

export function createSupabaseAdmin() {
  return createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  );
}
```

### Edge Function Template

```typescript
// functions/[name]/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { corsHeaders } from '../_shared/cors.ts';
import { createSupabaseAdmin } from '../_shared/supabase-client.ts';

serve(async (req: Request) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabase = createSupabaseAdmin();
    const body = await req.json();

    // ... 로직

    return new Response(JSON.stringify({ success: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
```

**config.toml에 등록:**
```toml
[functions.my-function]
verify_jwt = false  # webhook은 false, 사용자 호출은 true
```

---

## Commands

| Command | Description |
|---------|-------------|
| `supabase start` | 로컬 Supabase 시작 (`supabase/` 디렉토리에서) |
| `supabase stop` | 로컬 Supabase 중지 |
| `supabase status` | 서비스 상태 + 로컬 URL/키 확인 |
| `supabase db push` | 마이그레이션 적용 (원격) |
| `supabase db reset` | 로컬 DB 초기화 + 전체 마이그레이션 재실행 |
| `supabase migration new [name]` | 새 마이그레이션 파일 생성 |
| `supabase functions serve` | Edge Function 로컬 실행 |
| `supabase functions deploy [name]` | Edge Function 배포 |

---

## Checklist: 새 테이블 추가

1. `supabase migration new [description]` — 마이그레이션 파일 생성
2. CREATE TABLE + Indexes + Trigger + RLS — 위 템플릿 참조
3. `supabase db reset` — 로컬 검증
4. `edge/src/services/supabase.ts` — CRUD 서비스 함수 추가 (`/s3-edge`)
5. `docs/contracts/api-contracts.md` — API Contract 업데이트

## Checklist: RLS 정책 수정

1. 기존 정책 확인: `SELECT * FROM pg_policies WHERE tablename = '[table]'`
2. 마이그레이션에서 `DROP POLICY IF EXISTS` + `CREATE POLICY`
3. `supabase db reset` — 로컬 검증
4. 테스트: anon key로 다른 사용자 데이터 접근 불가 확인

---

## Related Skills

- `/s3-edge` — Edge API (Supabase CRUD 클라이언트)
- `/s3-backend` — Backend (service_role로 UPDATE)
- `/s3-build` — 전체 빌드 검증
- `/s3-test` — 전체 테스트 실행

---

## References

- [supabase-patterns.md](references/supabase-patterns.md) — 코드 템플릿 모음
- [Supabase README](C:\DK\S3\supabase\README.md) — Agent 작업 가이드
- [API Contract SSoT](C:\DK\S3\docs\contracts\api-contracts.md) — 엔드포인트 명세
