---
name: {SKILL_PREFIX}-test
description: |
  {PROJECT_NAME} Flutter 테스트 실행 및 결과 분석. 유닛/위젯/통합 테스트 지원.
  사용 시점: (1) PR 전 검증, (2) 기능 구현 후, (3) 버그 수정 후 회귀 테스트
  사용 금지: 단순 lint만 필요, 커버리지만 필요, 앱 실행 확인만
argument-hint: "[all|unit|widget|integration|feature-name]"
allowed-tools: Read, Grep, Glob, Bash
---

# {PROJECT_NAME} Test Skill

테스트를 실행하고 결과를 분석합니다.

## When to Use
- 코드 변경 후 검증할 때
- PR 생성 전 테스트 확인 시
- 특정 feature 테스트 필요 시

## When NOT to Use
- 단순 문법 검사 → `flutter analyze` 사용
- 타입 검사만 → IDE 사용
- 커버리지 리포트만 → `flutter test --coverage` 직접 실행

## Quick Start
```bash
/{SKILL_PREFIX}-test all           # 전체 테스트
/{SKILL_PREFIX}-test [feature]     # 특정 feature만
```

## Usage

```
/{SKILL_PREFIX}-test [scope]
```

### 스코프 옵션
- `all` - 전체 테스트 (기본값)
- `unit` - 유닛 테스트만
- `widget` - 위젯 테스트만
- `integration` - 통합 테스트만
- `[feature]` - 특정 feature 테스트

## 테스트 프로세스

### Step 1: Flutter 테스트
```bash
cd {PROJECT_DIR}
{FLUTTER_CMD} test
```

### Step 2: 특정 테스트 파일 실행
```bash
# 특정 파일
{FLUTTER_CMD} test test/features/[feature]/[test_file].dart

# 특정 feature
{FLUTTER_CMD} test test/features/[feature]/
```

### Step 3: 커버리지 리포트
```bash
{FLUTTER_CMD} test --coverage
```

## 테스트 구조

```
{PROJECT_DIR}/
└── test/
    ├── features/
    │   ├── [feature_a]/
    │   │   ├── [feature_a]_test.dart
    │   │   └── [feature_a]_provider_test.dart
    │   └── [feature_b]/
    │       └── [feature_b]_test.dart
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
  testWidgets('[Feature]Screen renders correctly', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(home: [Feature]Screen()),
      ),
    );
    expect(find.byType([Feature]Screen), findsOneWidget);
  });
}
```

### Provider 테스트 예시
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('[feature]Provider initial state', () {
    final container = ProviderContainer();
    final state = container.read([feature]Provider);
    expect(state, isNotNull);
  });
}
```

## 실패한 테스트 처리

테스트 실패 시 자동으로:
1. 에러 로그 분석
2. 관련 코드 파일 확인
3. 수정 제안

## 다음 단계

테스트 통과 후:
- `/{SKILL_PREFIX}-build` - 프로덕션 빌드
