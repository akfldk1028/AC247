# Flutter Build Troubleshooting Guide

## Common Issues

### 1. `pub get` 실패

**증상:** 의존성 설치 시 에러

**해결책:**
```bash
flutter pub cache clean
flutter pub get

# 또는 오프라인 모드로 시도
flutter pub get --offline
```

### 2. `build_runner` 에러

**증상:** 코드 생성 실패, `*.g.dart` 또는 `*.freezed.dart` 파일 에러

**해결책:**
```bash
flutter clean
flutter pub get
dart run build_runner clean
dart run build_runner build --delete-conflicting-outputs
```

### 3. Freezed 관련 에러

**증상:** `part` directive 에러, `fromJson` 없음

**체크리스트:**
1. `freezed_annotation` import 확인
2. `part` 파일 경로 확인
3. `@freezed` 어노테이션 확인

**올바른 구조:**
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

### 4. Riverpod Generator 에러

**증상:** Provider 생성 안됨

**체크리스트:**
1. `riverpod_annotation` import
2. `part '[file].g.dart'` 추가
3. `@riverpod` 어노테이션 위치

### 5. Web 빌드 실패

**해결책:**
```bash
flutter config --enable-web
flutter create . --platforms web
flutter clean
flutter pub get
flutter build web
```

### 6. Android 빌드 실패

**체크리스트:**
1. `android/app/build.gradle`의 `minSdkVersion` 확인 (최소 21)
2. `compileSdkVersion` 확인 (최신 권장)
3. Android SDK 설치 확인

## 디버깅 명령어

```bash
flutter doctor -v      # Flutter 환경 확인
flutter pub deps       # 의존성 확인
flutter analyze        # 분석 실행
flutter build web -v   # 상세 로그
```

## Auto-Claude 연동

복잡한 에러는 Auto-Claude 사용:
```bash
cd {CLONE_DIR}/apps/backend
.venv\Scripts\python.exe run.py --task "빌드 에러 해결: [에러 내용]"
```
