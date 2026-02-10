# Feature Templates

## Feature 구조 템플릿

새 feature 생성 시 다음 구조를 따릅니다:

```
{PROJECT_DIR}/lib/features/[feature_name]/
├── models/
│   └── [feature]_model.dart
├── mutations/
│   └── [action]_mutation.dart
├── queries/
│   └── get_[data]_query.dart
└── pages/
    ├── providers/
    │   └── [feature]_provider.dart
    ├── screens/
    │   └── [feature]_screen.dart
    └── widgets/
        └── [widget_name].dart
```

---

## 1. Model Template (Freezed)

### `models/[feature]_model.dart`
```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part '[feature]_model.freezed.dart';
part '[feature]_model.g.dart';

@freezed
class [Feature]Model with _$[Feature]Model {
  const factory [Feature]Model({
    required String id,
    required String name,
    String? description,
    required DateTime createdAt,
    DateTime? updatedAt,
  }) = _[Feature]Model;

  factory [Feature]Model.fromJson(Map<String, dynamic> json) =>
      _$[Feature]ModelFromJson(json);
}
```

---

## 2. Query Template (GET 요청)

### `queries/get_[feature]_query.dart`
```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/[feature]_model.dart';

part 'get_[feature]_query.g.dart';

@riverpod
Future<[Feature]Model> get[Feature]Query(
  Get[Feature]QueryRef ref, {
  required String id,
}) async {
  // TODO: implement data fetching
  throw UnimplementedError();
}

@riverpod
Future<List<[Feature]Model>> get[Feature]ListQuery(
  Get[Feature]ListQueryRef ref, {
  int page = 1,
  int limit = 20,
}) async {
  // TODO: implement list fetching
  throw UnimplementedError();
}
```

---

## 3. Mutation Template (POST/PUT/DELETE)

### `mutations/[action]_mutation.dart`
```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/[feature]_model.dart';

part '[action]_mutation.g.dart';

@riverpod
class Create[Feature]Mutation extends _$Create[Feature]Mutation {
  @override
  FutureOr<[Feature]Model?> build() => null;

  Future<[Feature]Model> call({required Map<String, dynamic> params}) async {
    state = const AsyncLoading();
    try {
      // TODO: implement creation
      throw UnimplementedError();
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }
}
```

---

## 4. Provider Template

### `pages/providers/[feature]_provider.dart`
```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part '[feature]_provider.g.dart';

@riverpod
class [Feature]PageNotifier extends _$[Feature]PageNotifier {
  @override
  Map<String, dynamic> build() => {};

  void update(String key, dynamic value) {
    state = {...state, key: value};
  }
}
```

---

## 5. Screen Template (Shadcn UI)

### `pages/screens/[feature]_screen.dart`
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

class [Feature]Screen extends ConsumerWidget {
  const [Feature]Screen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('[Feature]')),
      body: const Center(child: Text('TODO: implement')),
    );
  }
}
```

---

## 코드 생성 명령어

Feature 파일 생성 후 반드시 실행:

```bash
cd {PROJECT_DIR}
dart run build_runner build --delete-conflicting-outputs
```

Watch 모드 (개발 시 권장):

```bash
dart run build_runner watch --delete-conflicting-outputs
```
