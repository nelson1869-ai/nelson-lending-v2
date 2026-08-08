import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/token_storage_service.dart';

/// Callback invoked when a session refresh fails, forcing local logout.
typedef OnSessionExpired = void Function();

class ApiClient {
  late final Dio dio;
  final TokenStorageService _tokenStorage;
  OnSessionExpired? onSessionExpired;

  bool _isRefreshing = false;
  Future<bool>? _refreshFuture;

  ApiClient({
    required AppConfig config,
    required TokenStorageService tokenStorage,
    Dio? customDio,
    this.onSessionExpired,
  }) : _tokenStorage = tokenStorage {
    dio = customDio ??
        Dio(
          BaseOptions(
            baseUrl: config.apiBaseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 10),
            sendTimeout: const Duration(seconds: 10),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        );

    _setupInterceptors();
  }

  void _setupInterceptors() {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = _tokenStorage.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          if (error.response?.statusCode == 401 &&
              !error.requestOptions.path.contains('/owner/auth/login') &&
              !error.requestOptions.path.contains('/owner/auth/refresh')) {
            final refreshed = await _handle401Refresh();
            if (refreshed) {
              try {
                final opts = error.requestOptions;
                opts.headers['Authorization'] =
                    'Bearer ${_tokenStorage.accessToken}';
                final response = await dio.fetch(opts);
                return handler.resolve(response);
              } on DioException catch (retryError) {
                return handler.next(retryError);
              }
            } else {
              await _tokenStorage.clearAll();
              onSessionExpired?.call();
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  /// Single-flight serialized refresh mechanism to prevent token rotation race conditions.
  Future<bool> _handle401Refresh() async {
    if (_isRefreshing) {
      return (await _refreshFuture) ?? false;
    }

    _isRefreshing = true;
    _refreshFuture = _executeRefresh();

    try {
      final result = await _refreshFuture;
      return result ?? false;
    } finally {
      _isRefreshing = false;
      _refreshFuture = null;
    }
  }

  Future<bool> _executeRefresh() async {
    final currentRefreshToken = await _tokenStorage.getRefreshToken();
    if (currentRefreshToken == null || currentRefreshToken.isEmpty) {
      return false;
    }

    try {
      final refreshDio = Dio(BaseOptions(baseUrl: dio.options.baseUrl));
      final response = await refreshDio.post(
        '/api/v1/owner/auth/refresh',
        data: {'refreshToken': currentRefreshToken},
      );

      if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
        final data = response.data as Map<String, dynamic>;
        final newAccessToken =
            data['accessToken'] as String? ?? data['access_token'] as String;
        final newRefreshToken =
            data['refreshToken'] as String? ?? data['refresh_token'] as String;
        final expiresAtStr = data['accessTokenExpiresAt'] as String? ??
            data['access_token_expires_at'] as String;

        _tokenStorage.setAccessToken(
            newAccessToken, DateTime.parse(expiresAtStr));
        await _tokenStorage.saveRefreshToken(newRefreshToken);
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  return ApiClient(
    config: config,
    tokenStorage: tokenStorage,
  );
});
