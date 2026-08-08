import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/storage/token_storage_service.dart';
import '../data/owner_auth_repository.dart';
import '../domain/auth_state.dart';

class AuthController extends StateNotifier<AuthState> {
  final OwnerAuthRepository _repository;
  final TokenStorageService _tokenStorage;

  AuthController({
    required OwnerAuthRepository repository,
    required TokenStorageService tokenStorage,
  })  : _repository = repository,
        _tokenStorage = tokenStorage,
        super(const AuthState.initial());

  @override
  set state(AuthState value) => super.state = value;

  /// Attempts to restore existing session on startup.
  Future<void> restoreSession() async {
    final refreshToken = await _tokenStorage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      state = const AuthState.unauthenticated();
      return;
    }

    try {
      final pair = await _repository.refresh(refreshToken);
      _tokenStorage.setAccessToken(pair.accessToken, pair.expiresAt);
      await _tokenStorage.saveRefreshToken(pair.refreshToken);

      final owner = await _repository.getMe();
      state = AuthState.authenticated(owner);
    } catch (_) {
      await _tokenStorage.clearAll();
      state = const AuthState.unauthenticated();
    }
  }

  /// Authenticates Owner credentials.
  Future<bool> login(String username, String password) async {
    state = const AuthState.authenticating();

    try {
      final pair = await _repository.login(
        username: username.trim(),
        password: password,
      );

      _tokenStorage.setAccessToken(pair.accessToken, pair.expiresAt);
      await _tokenStorage.saveRefreshToken(pair.refreshToken);

      final owner = await _repository.getMe();
      state = AuthState.authenticated(owner);
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
    final refreshToken = await _tokenStorage.getRefreshToken();
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await _repository.logout(refreshToken);
    }
    await _tokenStorage.clearAll();
    state = const AuthState.unauthenticated();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  final repository = ref.watch(ownerAuthRepositoryProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);

  final controller = AuthController(
    repository: repository,
    tokenStorage: tokenStorage,
  );

  return controller;
});
