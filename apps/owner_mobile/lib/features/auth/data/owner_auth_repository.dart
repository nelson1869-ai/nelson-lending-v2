import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage_service.dart';
import '../domain/owner_profile.dart';

class TokenPairData {
  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;

  const TokenPairData({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
  });
}

class OwnerAuthRepository {
  final ApiClient _apiClient;
  final TokenStorageService _tokenStorage;

  OwnerAuthRepository({
    required ApiClient apiClient,
    required TokenStorageService tokenStorage,
  })  : _apiClient = apiClient,
        _tokenStorage = tokenStorage;

  Future<TokenPairData> login({
    required String username,
    required String password,
  }) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/owner/auth/login',
        data: {
          'username': username,
          'password': password,
        },
      );

      final data = response.data as Map<String, dynamic>;
      final accessToken = data['accessToken'] as String? ?? data['access_token'] as String;
      final refreshToken = data['refreshToken'] as String? ?? data['refresh_token'] as String;
      final expiresAtStr = data['accessTokenExpiresAt'] as String? ?? data['access_token_expires_at'] as String;

      return TokenPairData(
        accessToken: accessToken,
        refreshToken: refreshToken,
        expiresAt: DateTime.parse(expiresAtStr),
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  Future<TokenPairData> refresh(String refreshToken) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/owner/auth/refresh',
        data: {'refreshToken': refreshToken},
      );

      final data = response.data as Map<String, dynamic>;
      final accessToken = data['accessToken'] as String? ?? data['access_token'] as String;
      final newRefreshToken = data['refreshToken'] as String? ?? data['refresh_token'] as String;
      final expiresAtStr = data['accessTokenExpiresAt'] as String? ?? data['access_token_expires_at'] as String;

      return TokenPairData(
        accessToken: accessToken,
        refreshToken: newRefreshToken,
        expiresAt: DateTime.parse(expiresAtStr),
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  Future<void> logout(String refreshToken) async {
    try {
      await _apiClient.dio.post(
        '/api/v1/owner/auth/logout',
        data: {'refreshToken': refreshToken},
      );
    } catch (_) {
      // Ignore network failures during logout; local session is cleared regardless.
    }
  }

  Future<OwnerProfile> getMe() async {
    try {
      final response = await _apiClient.dio.get('/api/v1/owner/auth/me');
      return OwnerProfile.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  Future<bool> checkHealth() async {
    try {
      final response = await _apiClient.dio.get('/health/ready');
      return response.statusCode == 200;
    } catch (_) {
      try {
        final liveResp = await _apiClient.dio.get('/health/live');
        return liveResp.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
  }
}

final ownerAuthRepositoryProvider = Provider<OwnerAuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  return OwnerAuthRepository(
    apiClient: apiClient,
    tokenStorage: tokenStorage,
  );
});
