---
name: s3-test
description: |
  S3 Flutter 테스트 실행 및 결과 분석. 유닛/위젯/통합 테스트 지원.
  사용 시점: (1) PR 전 검증, (2) 기능 구현 후, (3) 버그 수정 후 회귀 테스트
  사용 금지: 단순 lint만 필요, 커버리지만 필요, 앱 실행 확인만
argument-hint: "[all|unit|widget|integration|feature-name]"
allowed-tools: Read, Grep, Glob, Bash
---

# S3 Test Skill

테스트를 실행하고 결과를 분석합니다.

## When to Use
- 코드 변경 후 검증할 때
- PR 생성 전 테스트 확인 시
- 특정 feature 테스트 필요 시
- 배포 전 전체 테스트 시

## When NOT to Use
- 단순 문법 검사 → `flutter analyze` 사용
- 타입 검사만 → IDE 활용
- 커버리지 리포트만 → `flutter test --coverage` 직접 실행

## Quick Start
```bash
/s3-test all      # 전체 테스트
/s3-test auth     # auth feature만
```

S3 프로젝트의 테스트를 실행하고 결과를 분석합니다.

## 사용법

```
/s3-test [scope]
```

### 스코프 옵션
- `all` - 전체 테스트 (기본값)
- `flutter` - Flutter 테스트만
- `unit` - 유닛 테스트만
- `widget` - 위젯 테스트만
- `integration` - 통합 테스트만
- `[feature]` - 특정 feature 테스트 (예: `auth`, `home`)

## 테스트 프로세스

### Step 1: Flutter 테스트
```bash
cd C:\DK\S3\S3\frontend
C:\DK\flutter\bin\flutter.bat test
```

### Step 2: 특정 테스트 파일 실행
```bash
# 특정 파일
C:\DK\flutter\bin\flutter.bat test test/features/auth/auth_test.dart

# 특정 feature
C:\DK\flutter\bin\flutter.bat test test/features/auth/
```

### Step 3: 커버리지 리포트
```bash
C:\DK\flutter\bin\flutter.bat test --coverage
```

## 테스트 구조

```
frontend/
└── test/
    ├── features/
    │   ├── auth/
    │   │   ├── login_test.dart
    │   │   └── auth_provider_test.dart
    │   ├── home/
    │   │   └── home_test.dart
    │   └── profile/
    │       └── profile_test.dart
    ├── widgets/
    │   └── common_widgets_test.dart
    └── test_helper.dart
```

## 테스트 작성 가이드

### Widget 테스트 예시
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('LoginScreen renders correctly', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(home: LoginScreen()),
      ),
    );

    expect(find.text('Welcome back'), findsOneWidget);
    expect(find.byType(ShadInputFormField), findsNWidgets(2));
  });
}
```

### Provider 테스트 예시
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('authProvider initial state', () {
    final container = ProviderContainer();
    final state = container.read(authProvider);

    expect(state.isAuthenticated, false);
  });
}
```

## 실패한 테스트 처리

테스트 실패 시 자동으로:
1. 에러 로그 분석
2. 관련 코드 파일 확인
3. 수정 제안

### Auto-Claude 연동
복잡한 테스트 실패는 Auto-Claude의 QA 에이전트 활용:

```bash
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe run.py --qa --task "테스트 실패 수정"
```

## 다음 단계

테스트 통과 후:
- `/s3-build` - 프로덕션 빌드
- `/s3-deploy` - 배포
