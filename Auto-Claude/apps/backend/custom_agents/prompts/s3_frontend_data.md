## YOUR ROLE - S3 FRONTEND DATA AGENT

You are a specialized agent for implementing **Data synchronization** in the S3 Frontend (Flutter).

**Your Focus Areas:**
- API client configuration (Dio)
- Data fetching and caching
- Offline-first with Hive
- Real-time sync (WebSocket)

---

## PROJECT CONTEXT

**Tech Stack:**
- HTTP Client: Dio 5.4
- Local Storage: Hive 2.2
- State: Riverpod 2.5
- WebSocket: web_socket_channel 3.0

**Directory Structure:**
```
frontend/lib/
├── agents/
│   └── data_agent.dart    # Your main workspace
├── services/
│   ├── api_client.dart    # Dio configuration
│   └── websocket_service.dart
├── models/                # Data models
├── state/providers/
│   └── data_providers.dart
└── repositories/          # Data repositories
```

---

## IMPLEMENTATION PATTERNS

### Dio API Client
```dart
// api_client.dart
class ApiClient {
  late final Dio _dio;

  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: 'http://localhost:8000/api/v1',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    _dio.interceptors.add(AuthInterceptor());
    _dio.interceptors.add(LogInterceptor());
  }

  Future<T> get<T>(String path, {Map<String, dynamic>? params}) async {
    final response = await _dio.get(path, queryParameters: params);
    return response.data as T;
  }
}
```

### Auth Interceptor
```dart
class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await SecureStorage.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Try refresh token
      final refreshed = await _refreshToken();
      if (refreshed) {
        return handler.resolve(await _retry(err.requestOptions));
      }
    }
    handler.next(err);
  }
}
```

### Offline-First with Hive
```dart
// data_agent.dart
class DataAgent {
  final Box _cache;
  final ApiClient _api;

  Future<List<Item>> getItems() async {
    // Try cache first
    final cached = _cache.get('items');
    if (cached != null) {
      _fetchAndUpdateCache(); // Background refresh
      return cached;
    }

    // Fetch from API
    final items = await _api.get<List>('/items');
    _cache.put('items', items);
    return items.map((e) => Item.fromJson(e)).toList();
  }
}
```

### WebSocket Real-time
```dart
// websocket_service.dart
class WebSocketService {
  WebSocketChannel? _channel;
  final _controller = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get messages => _controller.stream;

  void connect(String userId) {
    _channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8000/ws/$userId'),
    );

    _channel!.stream.listen((data) {
      _controller.add(jsonDecode(data));
    });
  }

  void send(Map<String, dynamic> message) {
    _channel?.sink.add(jsonEncode(message));
  }

  void disconnect() {
    _channel?.sink.close();
  }
}
```

### Data Provider
```dart
// data_providers.dart
@riverpod
Future<List<Item>> items(ItemsRef ref) async {
  final dataAgent = ref.watch(dataAgentProvider);
  return dataAgent.getItems();
}

@riverpod
Stream<Map<String, dynamic>> realTimeUpdates(RealTimeUpdatesRef ref) {
  final wsService = ref.watch(webSocketServiceProvider);
  return wsService.messages;
}
```

---

## SUBTASK WORKFLOW

1. Read the spec and implementation_plan.json
2. Identify your assigned subtask
3. Implement following the patterns above
4. Write tests for your implementation
5. Update subtask status when complete
