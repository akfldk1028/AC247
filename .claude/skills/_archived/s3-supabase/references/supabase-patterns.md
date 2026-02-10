# Supabase Patterns — 코드 템플릿 모음

> 실제 `supabase/` 코드에서 추출한 패턴. 새 마이그레이션/함수 작성 시 이 템플릿을 따를 것.

---

## 1. Complete Migration Template (New Table)

```sql
-- Migration: create_[table_name]
-- Description: [테이블 설명]

-- ============================================================
-- 1. Table
-- ============================================================
CREATE TABLE IF NOT EXISTS [table_name] (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- Core fields
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'error')),

    -- URL fields
    source_url TEXT,
    result_url TEXT,

    -- JSON fields (JSONB for queries, not TEXT)
    labels JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Numeric
    score FLOAT,
    count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps (always include both)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. Indexes (FK columns + frequent query filters)
-- ============================================================
CREATE INDEX idx_[table]_user_id ON [table_name](user_id);
CREATE INDEX idx_[table]_project_id ON [table_name](project_id);
CREATE INDEX idx_[table]_status ON [table_name](status);
CREATE INDEX idx_[table]_created_at ON [table_name](created_at DESC);

-- ============================================================
-- 3. Auto-update trigger
-- ============================================================
CREATE TRIGGER [table_name]_updated_at
    BEFORE UPDATE ON [table_name]
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 4. RLS
-- ============================================================
ALTER TABLE [table_name] ENABLE ROW LEVEL SECURITY;

-- SELECT: owner only
CREATE POLICY "Users can view own [table]"
    ON [table_name] FOR SELECT
    USING (auth.uid() = user_id);

-- INSERT: owner only
CREATE POLICY "Users can create own [table]"
    ON [table_name] FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- UPDATE: owner only
CREATE POLICY "Users can update own [table]"
    ON [table_name] FOR UPDATE
    USING (auth.uid() = user_id);

-- DELETE: owner only
CREATE POLICY "Users can delete own [table]"
    ON [table_name] FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================
-- 5. Realtime (선택사항 — 실시간 업데이트 필요한 테이블만)
-- ============================================================
-- ALTER PUBLICATION supabase_realtime ADD TABLE [table_name];
```

---

## 2. Add Column Migration Template

```sql
-- Migration: add_[column]_to_[table]
-- Description: [table]에 [column] 필드 추가

ALTER TABLE [table_name]
    ADD COLUMN [column_name] TEXT;  -- nullable (기존 데이터 호환)

-- 또는 NOT NULL with default:
ALTER TABLE [table_name]
    ADD COLUMN [column_name] INTEGER NOT NULL DEFAULT 0;

-- Index (자주 쿼리하는 컬럼만)
CREATE INDEX idx_[table]_[column] ON [table_name]([column_name]);
```

---

## 3. Modify RLS Migration Template

```sql
-- Migration: update_rls_[table]_[description]
-- Description: [table] RLS 정책 수정

-- 기존 정책 삭제
DROP POLICY IF EXISTS "Old policy name" ON [table_name];

-- 새 정책 추가
CREATE POLICY "New policy name"
    ON [table_name] FOR SELECT
    USING (
        auth.uid() = user_id
        OR EXISTS (
            SELECT 1 FROM [related_table]
            WHERE [related_table].id = [table_name].[fk_column]
            AND [related_table].user_id = auth.uid()
        )
    );
```

---

## 4. Actual Schema: users_profile

```sql
CREATE TABLE IF NOT EXISTS users_profile (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    tier TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'pro', 'enterprise')),
    credits INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger
CREATE TRIGGER users_profile_updated_at
    BEFORE UPDATE ON users_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- RLS (self-referential: id = auth.uid())
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON users_profile FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON users_profile FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON users_profile FOR INSERT WITH CHECK (auth.uid() = id);
```

---

## 5. Actual Schema: projects

```sql
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);

CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own projects"
    ON projects FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own projects"
    ON projects FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects"
    ON projects FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE USING (auth.uid() = user_id);
```

---

## 6. Actual Schema: segmentation_results

```sql
CREATE TABLE IF NOT EXISTS segmentation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    source_image_url TEXT NOT NULL,
    mask_image_url TEXT,
    text_prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'error')),
    labels JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_segmentation_results_user_id ON segmentation_results(user_id);
CREATE INDEX idx_segmentation_results_project_id ON segmentation_results(project_id);
CREATE INDEX idx_segmentation_results_status ON segmentation_results(status);
CREATE INDEX idx_segmentation_results_created_at ON segmentation_results(created_at DESC);

CREATE TRIGGER segmentation_results_updated_at
    BEFORE UPDATE ON segmentation_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

ALTER TABLE segmentation_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own results"
    ON segmentation_results FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own results"
    ON segmentation_results FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own results"
    ON segmentation_results FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own results"
    ON segmentation_results FOR DELETE USING (auth.uid() = user_id);

-- Realtime (추론 상태 실시간 알림)
ALTER PUBLICATION supabase_realtime ADD TABLE segmentation_results;
```

---

## 7. Actual Schema: usage_logs

```sql
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    credits_used INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    -- 주의: updated_at 없음 (로그는 불변)
);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at DESC);

-- 주의: trigger 없음 (로그는 불변, updated_at 없음)

ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- SELECT: 자신의 로그만
CREATE POLICY "Users can view own usage"
    ON usage_logs FOR SELECT USING (auth.uid() = user_id);

-- INSERT: service_role만 (Backend에서 사용)
CREATE POLICY "Service role can insert usage"
    ON usage_logs FOR INSERT WITH CHECK (true);
```

---

## 8. Auth Trigger Template (새 트리거)

```sql
-- 새 auth 트리거가 필요한 경우 (예: 프로필 업데이트 시 로그)
CREATE OR REPLACE FUNCTION on_profile_updated()
RETURNS TRIGGER AS $$
BEGIN
    -- 크레딧 변경 로그
    IF OLD.credits != NEW.credits THEN
        INSERT INTO usage_logs (user_id, action, credits_used, metadata)
        VALUES (
            NEW.id,
            'credit_change',
            OLD.credits - NEW.credits,
            jsonb_build_object('old_credits', OLD.credits, 'new_credits', NEW.credits)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_profile_updated_trigger
    AFTER UPDATE ON users_profile
    FOR EACH ROW
    EXECUTE FUNCTION on_profile_updated();
```

---

## 9. Edge Function Template (Complete)

```typescript
// supabase/functions/[name]/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { corsHeaders } from '../_shared/cors.ts';
import { createSupabaseAdmin } from '../_shared/supabase-client.ts';

serve(async (req: Request) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // 1. API Key 검증 (webhook용)
    const apiKey = req.headers.get('X-API-Key');
    if (apiKey !== Deno.env.get('API_SECRET_KEY')) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 2. Body 파싱
    const { task_id, status, mask_url, labels, metadata } = await req.json();

    // 3. Supabase Admin client (service_role)
    const supabase = createSupabaseAdmin();

    // 4. DB 작업
    const { error } = await supabase
      .from('segmentation_results')
      .update({
        status,
        mask_image_url: mask_url,
        labels,
        metadata,
      })
      .eq('id', task_id);

    if (error) throw error;

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

**config.toml 등록:**
```toml
[functions.[name]]
verify_jwt = false  # webhook = false, user API = true
```

---

## 10. Seed Data Template

```sql
-- supabase/seed.sql
-- Run with: supabase db reset

-- Note: auth.users에 직접 INSERT하면 handle_new_user trigger가
-- users_profile을 자동 생성. seed에서는 auth.users를 건드리지 말 것.

-- 테스트용 프로젝트 (auth user UUID를 알아야 함)
-- INSERT INTO projects (user_id, name, description) VALUES
--   ('<user-uuid>', 'Test Project', 'For local testing');

-- 테스트용 세그멘테이션 결과
-- INSERT INTO segmentation_results (user_id, project_id, source_image_url, text_prompt, status) VALUES
--   ('<user-uuid>', '<project-uuid>', 'https://example.com/test.png', 'cat', 'done');
```

---

## 11. Useful SQL Queries (Debug)

```sql
-- 모든 RLS 정책 확인
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname = 'public';

-- 특정 테이블 RLS 확인
SELECT * FROM pg_policies WHERE tablename = 'segmentation_results';

-- Realtime publication 확인
SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';

-- 트리거 확인
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public';

-- 인덱스 확인
SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public';
```

---

## 12. config.toml Key Settings

```toml
[project]
id = "s3-app"

[db]
port = 54322
major_version = 15

[auth]
enabled = true
site_url = "http://localhost:3000"

[auth.email]
enable_signup = true
enable_confirmations = false  # 로컬 개발용

[storage]
file_size_limit = "50MiB"

[realtime]
enabled = true

[functions.process-webhook]
verify_jwt = false
```
