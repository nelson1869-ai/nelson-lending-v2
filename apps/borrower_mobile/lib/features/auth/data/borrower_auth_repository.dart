import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';
import '../domain/borrower_profile.dart';

class BorrowerTokenPair {
  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;

  const BorrowerTokenPair({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
  });

  factory BorrowerTokenPair.fromJson(Map<String, dynamic> json) {
    final accessToken =
        json['accessToken'] as String? ?? json['access_token'] as String;
    final refreshToken =
        json['refreshToken'] as String? ?? json['refresh_token'] as String;
    final expiresAtStr = json['accessTokenExpiresAt'] as String? ??
        json['access_token_expires_at'] as String;

    return BorrowerTokenPair(
      accessToken: accessToken,
      refreshToken: refreshToken,
      expiresAt: DateTime.parse(expiresAtStr),
    );
  }
}

class BorrowerAuthRepository {
  final ApiClient _apiClient;

  BorrowerAuthRepository({required ApiClient apiClient})
      : _apiClient = apiClient;

  /// Authenticates Borrower credentials.
  Future<BorrowerTokenPair> login({
    required String phoneNumber,
    required String pin,
    required String deviceIdentifier,
    String platform = 'android',
  }) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/borrower/auth/login',
        data: {
          'phoneNumber': phoneNumber,
          'pin': pin,
          'deviceIdentifier': deviceIdentifier,
          'platform': platform,
        },
      );
      return BorrowerTokenPair.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  /// Rotates refresh session token.
  Future<BorrowerTokenPair> refresh({
    required String refreshToken,
    required String deviceIdentifier,
  }) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/borrower/auth/refresh',
        data: {
          'refreshToken': refreshToken,
          'deviceIdentifier': deviceIdentifier,
        },
      );
      return BorrowerTokenPair.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  /// Fetches authenticated Borrower profile.
  Future<BorrowerProfile> getMe() async {
    try {
      final response = await _apiClient.dio.get('/api/v1/borrower/auth/me');
      return BorrowerProfile.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }

  /// Revokes refresh session.
  Future<void> logout(String refreshToken) async {
    try {
      await _apiClient.dio.post(
        '/api/v1/borrower/auth/logout',
        data: {'refreshToken': refreshToken},
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }
}

final borrowerAuthRepositoryProvider = Provider<BorrowerAuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BorrowerAuthRepository(apiClient: apiClient);
});
