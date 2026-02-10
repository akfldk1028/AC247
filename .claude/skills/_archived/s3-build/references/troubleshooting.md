# Flutter Build Troubleshooting Guide

## Common Issues

### 1. `pub get` ?�패

**증상:** ?�존???�치 �??�러

**?�결�?**
```bash
# 캐시 ?�리??
flutter pub cache clean
flutter pub get

# ?�는 ?�프?�인 모드�??�도
flutter pub get --offline
```

### 2. `build_runner` ?�러

**증상:** 코드 ?�성 ?�패, `*.g.dart` ?�는 `*.freezed.dart` ?�일 ?�러

**?�결�?**
```bash
# 기존 ?�성 ?�일 ??�� ???�생??
flutter clean
flutter pub get
dart run build_runner clean
dart run build_runner build --delete-conflicting-outputs
```

### 3. Freezed 관???�러

**증상:** `part` directive ?�러, `fromJson` ?�음

**체크리스??**
1. `freezed_annotation` import ?�인
2. `part` ?�일 경로 ?�인
3. `@freezed` ?�노?�이???�인

**?�바�?구조:**
```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    required String id,
    required String name,
  }) = _UserModel;

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);
}
```

### 4. Riverpod Generator ?�러

**증상:** Provider ?�성 ?�됨

**체크리스??**
1. `riverpod_annotation` import
2. `part '[file].g.dart'` 추�?
3. `@riverpod` ?�노?�이???�치

### 5. Web 빌드 ?�패

**증상:** `flutter build web` ?�러

**?�결�?**
```bash
# Web 지???�성??
flutter config --enable-web
flutter create . --platforms web

# ?�린 빌드
flutter clean
flutter pub get
flutter build web
```

### 6. Android 빌드 ?�패

**증상:** Gradle ?�러, SDK 버전 문제

**체크리스??**
1. `android/app/build.gradle`??`minSdkVersion` ?�인 (최소 21)
2. `compileSdkVersion` ?�인 (최신 권장)
3. Android SDK ?�치 ?�인

### 7. Shadcn UI 관???�러

**증상:** `ShadApp`, `ShadButton` ??�?찾음

**?�결�?**
```bash
# pubspec.yaml ?�인
# shadcn_ui: ^0.45.1

flutter pub get
```

**?�바�?import:**
```dart
import 'package:shadcn_ui/shadcn_ui.dart';
```

## ?�버�?명령??

```bash
# Flutter ?�경 ?�인
flutter doctor -v

# ?�존???�인
flutter pub deps

# 분석 ?�행
flutter analyze

# ?�세??로그
flutter build web -v
```

## ?�용???�정

### pubspec.yaml ?�시 (dependencies)
```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.6.1
  riverpod_annotation: ^2.6.1
  go_router: ^14.6.2
  dio: ^5.7.0
  freezed_annotation: ^2.4.4
  json_annotation: ^4.9.0
  shadcn_ui: ^0.45.1

dev_dependencies:
  build_runner: ^2.4.13
  riverpod_generator: ^2.6.2
  freezed: ^2.5.7
  json_serializable: ^6.8.0
```

## Auto-Claude ?�동

복잡???�러??Auto-Claude ?�용:
```bash
cd C:\DK\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe run.py --task "빌드 ?�러 ?�결: [?�러 ?�용]"
```
