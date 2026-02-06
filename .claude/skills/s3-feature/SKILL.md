---
name: s3-feature
description: |
  S3 새 기능 개발 워크플로우. Feature-First 구조로 파일 생성, Freezed 모델, Riverpod 상태관리 포함.
  사용 시점: (1) 새 기능 추가 시, (2) 새 화면 개발 시, (3) API 연동 기능 구현 시
  사용 금지: 기존 기능 수정, 단순 UI 수정, 버그 수정, 리팩토링
argument-hint: "[기능 설명]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# S3 Feature Development Skill

Feature-First 아키텍처로 새 기능을 개발합니다.

## When to Use
- 새로운 화면/기능 추가할 때
- CRUD 기능 구현 시
- API 연동이 필요한 기능 개발 시
- Backend + Frontend 동시 개발 시

## When NOT to Use
- 기존 기능 수정 → 직접 파일 수정
- 단순 UI 수정 → 직접 위젯 수정
- 버그 수정 → 해당 파일 직접 수정
- 리팩토링 → 기존 구조 유지

## Quick Start
```bash
/s3-feature "사용자 프로필 수정"
/s3-feature "푸시 알림 설정"
```

새로운 기능을 체계적으로 개발합니다. Backend와 Frontend 작업을 자동으로 분석하고 필요한 파일 구조를 생성합니다.

## 사용법

```
/s3-feature "기능 설명"
```

### 예시
```
/s3-feature "사용자 프로필 수정"
/s3-feature "푸시 알림 구현"
/s3-feature "소셜 로그인 추가"
/s3-feature "결제 시스템 연동"
```

## 워크플로우

### Phase 1: 요구사항 분석
1. 기능 범위 파악
2. Backend/Frontend 작업 분리
3. 필요한 API 엔드포인트 식별
4. 데이터 모델 설계

### Phase 2: 파일 구조 생성

#### Frontend (Flutter) - Feature-First Architecture
```
frontend/lib/features/[feature_name]/
├── models/
│   └── [feature]_model.dart          # Freezed 모델
├── mutations/
│   └── [action]_mutation.dart        # POST/PUT/DELETE
├── queries/
│   └── get_[data]_query.dart         # GET 요청
└── pages/
    ├── providers/
    │   └── [feature]_provider.dart   # Riverpod 상태
    ├── screens/
    │   └── [feature]_screen.dart     # 화면 위젯
    └── widgets/
        └── [component].dart          # 재사용 위젯
```

### Phase 3: 코드 생성
1. Freezed 모델 생성
2. Riverpod provider 생성
3. API 연동 코드 (Dio)
4. UI 컴포넌트 (Shadcn UI)

### Phase 4: Auto-Claude 연동

복잡한 기능은 전문 에이전트 활용:

| 작업 | 에이전트 |
|------|---------|
| 인증 Backend | `s3_backend_auth` |
| 데이터 CRUD | `s3_backend_data` |
| 알림 시스템 | `s3_backend_notification` |
| AI 기능 | `s3_ai_assistant` |
| 인증 UI | `s3_frontend_auth` |
| 데이터 UI | `s3_frontend_data` |

## Feature 템플릿

### Model (Freezed)
```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part '[feature]_model.freezed.dart';
part '[feature]_model.g.dart';

@freezed
class [Feature]Model with _$[Feature]Model {
  const factory [Feature]Model({
    required String id,
    required String name,
    // ... fields
  }) = _[Feature]Model;

  factory [Feature]Model.fromJson(Map<String, dynamic> json) =>
      _$[Feature]ModelFromJson(json);
}
```

### Query (Riverpod)
```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'get_[feature]_query.g.dart';

@riverpod
Future<[Feature]Model> get[Feature]Query(Get[Feature]QueryRef ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get('/api/[feature]');
  return [Feature]Model.fromJson(response.data);
}
```

### Mutation (Riverpod)
```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part '[action]_mutation.g.dart';

@riverpod
class [Action]Mutation extends _$[Action]Mutation {
  @override
  FutureOr<[Response]?> build() => null;

  Future<[Response]> call({required [Params] params}) async {
    state = const AsyncLoading();
    try {
      final dio = ref.read(dioProvider);
      final response = await dio.post('/api/[endpoint]', data: params.toJson());
      final result = [Response].fromJson(response.data);
      state = AsyncData(result);
      return result;
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }
}
```

### Screen (Shadcn UI)
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

class [Feature]Screen extends ConsumerWidget {
  const [Feature]Screen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dataAsync = ref.watch(get[Feature]QueryProvider);

    return Scaffold(
      body: dataAsync.when(
        data: (data) => _buildContent(data),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
```

## 코드 생성 후

파일 생성 후 반드시 실행:
```bash
cd C:\DK\S3\S3\frontend
dart run build_runner build --delete-conflicting-outputs
```

## 관련 Skills

- `/s3-build` - 빌드 실행
- `/s3-test` - 테스트 실행
- `/s3-deploy` - 배포

## Auto-Claude Spec 생성

대규모 기능 개발 시 Auto-Claude spec 생성:
```bash
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe spec_runner.py --task "[기능 설명]"
```
