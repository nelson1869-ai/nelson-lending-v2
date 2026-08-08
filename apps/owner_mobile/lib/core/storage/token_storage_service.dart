import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure token storage service.
/// High-entropy refresh token is persisted in FlutterSecureStorage.
/// Short-lived access token is held in memory for security.
class TokenStorageService {
  static const _refreshTokenKey = 'owner_refresh_token';
  final FlutterSecureStorage _storage;

  String? _accessToken;
  DateTime? _accessTokenExpiresAt;

  TokenStorageService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  /// Access token (memory-first).
  String? get accessToken => _accessToken;
  DateTime? get accessTokenExpiresAt => _accessTokenExpiresAt;

  bool get hasValidAccessToken {
    if (_accessToken == null || _accessTokenExpiresAt == null) return false;
    return DateTime.now().isBefore(_accessTokenExpiresAt!);
  }

  void setAccessToken(String token, DateTime expiresAt) {
    _accessToken = token;
    _accessTokenExpiresAt = expiresAt;
  }

  void clearAccessToken() {
    _accessToken = null;
    _accessTokenExpiresAt = null;
  }

  /// Refresh token (persisted securely).
  Future<String?> getRefreshToken() async {
    try {
      return await _storage.read(key: _refreshTokenKey);
    } catch (_) {
      return null;
    }
  }

  /// Save or rotate refresh token.
  Future<void> saveRefreshToken(String refreshToken) async {
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  /// Delete refresh token from secure storage.
  Future<void> deleteRefreshToken() async {
    await _storage.delete(key: _refreshTokenKey);
  }

  /// Clear all stored tokens (memory + secure storage).
  Future<void> clearAll() async {
    clearAccessToken();
    await deleteRefreshToken();
  }
}

final tokenStorageProvider = Provider<TokenStorageService>((ref) {
  return TokenStorageService();
});
