import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorageService {
  final FlutterSecureStorage _storage;

  static const String _refreshTokenKey = 'borrower_refresh_token';
  static const String _deviceIdKey = 'borrower_device_identifier';

  String? _accessToken;
  DateTime? _accessTokenExpiresAt;

  TokenStorageService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  String? get accessToken => _accessToken;
  DateTime? get accessTokenExpiresAt => _accessTokenExpiresAt;

  void setAccessToken(String token, DateTime expiresAt) {
    _accessToken = token;
    _accessTokenExpiresAt = expiresAt;
  }

  void clearAccessToken() {
    _accessToken = null;
    _accessTokenExpiresAt = null;
  }

  Future<void> saveRefreshToken(String refreshToken) async {
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  Future<void> saveDeviceIdentifier(String deviceId) async {
    await _storage.write(key: _deviceIdKey, value: deviceId);
  }

  Future<String?> getDeviceIdentifier() async {
    return await _storage.read(key: _deviceIdKey);
  }

  Future<void> clearAll() async {
    clearAccessToken();
    await _storage.delete(key: _refreshTokenKey);
  }
}

final tokenStorageProvider = Provider<TokenStorageService>((ref) {
  return TokenStorageService();
});
