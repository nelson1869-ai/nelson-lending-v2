import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/device_service.dart';
import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage_service.dart';
import '../data/borrower_auth_repository.dart';
import '../domain/auth_state.dart';

class AuthController extends StateNotifier<AuthState> {
  final BorrowerAuthRepository _repository;
  final TokenStorageService _tokenStorage;
  final DeviceService _deviceService;

  AuthController({
    required BorrowerAuthRepository repository,
    required TokenStorageService tokenStorage,
    required DeviceService deviceService,
  })  : _repository = repository,
        _tokenStorage = tokenStorage,
        _deviceService = deviceService,
        super(const AuthState.initial());

  @override
  set state(AuthState value) => super.state = value;

  /// Handles automatic session expiration triggered by API client refresh failure.
  void handleSessionExpired() {
    state = const AuthState.unauthenticated(
        'Session expired. Please sign in again.');
  }

  /// Attempts to restore existing session on startup.
  Future<void> restoreSession() async {
    final refreshToken = await _tokenStorage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      state = const AuthState.unauthenticated();
      return;
    }

    try {
      final deviceId = await _deviceService.getOrCreateDeviceIdentifier();
      final pair = await _repository.refresh(
        refreshToken: refreshToken,
        deviceIdentifier: deviceId,
      );

      _tokenStorage.setAccessToken(pair.accessToken, pair.expiresAt);
      await _tokenStorage.saveRefreshToken(pair.refreshToken);

      final profile = await _repository.getMe();
      state = AuthState.authenticated(profile);
    } catch (_) {
      await _tokenStorage.clearAll();
      state = const AuthState.unauthenticated();
    }
  }

  /// Authenticates Borrower credentials.
  Future<bool> login(String phoneNumber, String pin) async {
    state = const AuthState.authenticating();

    try {
      final deviceId = await _deviceService.getOrCreateDeviceIdentifier();
      final pair = await _repository.login(
        phoneNumber: phoneNumber.trim(),
        pin: pin.trim(),
        deviceIdentifier: deviceId,
      );

      _tokenStorage.setAccessToken(pair.accessToken, pair.expiresAt);
      await _tokenStorage.saveRefreshToken(pair.refreshToken);

      final profile = await _repository.getMe();
      state = AuthState.authenticated(profile);
      return true;
    } on AppException catch (e) {
      await _tokenStorage.clearAll();
      state = AuthState.unauthenticated(e.message);
      return false;
    } catch (_) {
      await _tokenStorage.clearAll();
      state = const AuthState.unauthenticated('Invalid credentials');
      return false;
    }
  }

  /// Revokes refresh session and clears local tokens.
  Future<void> logout() async {
    try {
      final refreshToken = await _tokenStorage.getRefreshToken();
      if (refreshToken != null && refreshToken.isNotEmpty) {
        await _repository.logout(refreshToken);
      }
    } catch (_) {
      // Remote revocation is best effort. Local logout must always succeed.
    } finally {
      await _tokenStorage.clearAll();
      state = const AuthState.unauthenticated();
    }
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  final repository = ref.watch(borrowerAuthRepositoryProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  final deviceService = ref.watch(deviceServiceProvider);
  final apiClient = ref.watch(apiClientProvider);

  final controller = AuthController(
    repository: repository,
    tokenStorage: tokenStorage,
    deviceService: deviceService,
  );

  apiClient.onSessionExpired = controller.handleSessionExpired;

  return controller;
});
