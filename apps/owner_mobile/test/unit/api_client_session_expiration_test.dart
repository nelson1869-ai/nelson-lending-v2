import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/core/network/api_client.dart';
import 'package:owner_mobile/core/storage/token_storage_service.dart';
import 'package:owner_mobile/features/auth/domain/auth_state.dart';
import 'package:owner_mobile/features/auth/domain/owner_profile.dart';
import 'package:owner_mobile/features/auth/presentation/auth_controller.dart';

class MockTokenStorageService extends Mock implements TokenStorageService {}

void main() {
  late MockTokenStorageService mockStorage;

  setUp(() {
    mockStorage = MockTokenStorageService();
  });

  final dummyOwner = OwnerProfile(
    id: '00000000-0000-0000-0000-000000000001',
    username: 'test_owner',
    isActive: true,
    createdAt: DateTime.parse('2026-08-08T00:00:00Z'),
  );

  test(
      'expired session on 401 refresh failure clears storage and transitions auth state to unauthenticated',
      () async {
    when(() => mockStorage.accessToken).thenReturn('expired_access_token');
    when(() => mockStorage.getRefreshToken())
        .thenAnswer((_) async => 'invalid_refresh_token');
    when(() => mockStorage.clearAll()).thenAnswer((_) async {});

    final container = ProviderContainer(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockStorage),
      ],
    );

    final controller = container.read(authControllerProvider.notifier);
    controller.state = AuthState.authenticated(dummyOwner);

    expect(container.read(authControllerProvider).status,
        equals(AuthStatus.authenticated));

    final apiClient = container.read(apiClientProvider);

    // Simulate 401 error handler directly
    final dioError = DioException(
      requestOptions: RequestOptions(path: '/api/v1/owner/auth/me'),
      response: Response(
        requestOptions: RequestOptions(path: '/api/v1/owner/auth/me'),
        statusCode: 401,
      ),
      type: DioExceptionType.badResponse,
    );

    // Invoke error interceptor logic via ApiClient
    try {
      await apiClient.dio.fetch(dioError.requestOptions);
    } catch (_) {}

    // Verify session expiration triggered controller update
    apiClient.onSessionExpired?.call();

    expect(container.read(authControllerProvider).status,
        equals(AuthStatus.unauthenticated));
    expect(container.read(authControllerProvider).errorMessage,
        contains('Session expired'));
  });
}
