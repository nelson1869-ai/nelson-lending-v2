import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/core/errors/app_exception.dart';
import 'package:owner_mobile/core/storage/token_storage_service.dart';
import 'package:owner_mobile/features/auth/data/owner_auth_repository.dart';
import 'package:owner_mobile/features/auth/domain/auth_state.dart';
import 'package:owner_mobile/features/auth/domain/owner_profile.dart';
import 'package:owner_mobile/features/auth/presentation/auth_controller.dart';

class MockOwnerAuthRepository extends Mock implements OwnerAuthRepository {}

class MockTokenStorageService extends Mock implements TokenStorageService {}

void main() {
  late MockOwnerAuthRepository mockRepo;
  late MockTokenStorageService mockStorage;
  late AuthController controller;

  setUp(() {
    mockRepo = MockOwnerAuthRepository();
    mockStorage = MockTokenStorageService();
    controller =
        AuthController(repository: mockRepo, tokenStorage: mockStorage);
  });

  final dummyOwner = OwnerProfile(
    id: '00000000-0000-0000-0000-000000000001',
    username: 'owner',
    isActive: true,
    createdAt: DateTime.parse('2026-08-08T00:00:00Z'),
  );

  final dummyPair = TokenPairData(
    accessToken: 'test_access',
    refreshToken: 'test_refresh',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );

  group('AuthController', () {
    test(
        'restoreSession transitions to unauthenticated when no stored token exists',
        () async {
      when(() => mockStorage.getRefreshToken()).thenAnswer((_) async => null);

      await controller.restoreSession();

      expect(controller.state.status, equals(AuthStatus.unauthenticated));
    });

    test('restoreSession restores session when valid refresh token exists',
        () async {
      when(() => mockStorage.getRefreshToken())
          .thenAnswer((_) async => 'valid_refresh');
      when(() => mockRepo.refresh('valid_refresh'))
          .thenAnswer((_) async => dummyPair);
      when(() => mockRepo.getMe()).thenAnswer((_) async => dummyOwner);
      when(() => mockStorage.saveRefreshToken(any())).thenAnswer((_) async {});

      await controller.restoreSession();

      expect(controller.state.status, equals(AuthStatus.authenticated));
      expect(controller.state.owner?.username, equals('owner'));
    });

    test('restoreSession clears session on failed refresh', () async {
      when(() => mockStorage.getRefreshToken())
          .thenAnswer((_) async => 'invalid_refresh');
      when(() => mockRepo.refresh('invalid_refresh'))
          .thenThrow(const UnauthorizedException());
      when(() => mockStorage.clearAll()).thenAnswer((_) async {});

      await controller.restoreSession();

      expect(controller.state.status, equals(AuthStatus.unauthenticated));
      verify(() => mockStorage.clearAll()).called(1);
    });

    test('login success authenticates Owner', () async {
      when(() => mockRepo.login(username: 'owner', password: 'password123'))
          .thenAnswer((_) async => dummyPair);
      when(() => mockStorage.saveRefreshToken(any())).thenAnswer((_) async {});
      when(() => mockRepo.getMe()).thenAnswer((_) async => dummyOwner);

      final success = await controller.login('owner', 'password123');

      expect(success, isTrue);
      expect(controller.state.status, equals(AuthStatus.authenticated));
      expect(controller.state.owner?.username, equals('owner'));
    });

    test('login failure sets unauthenticated with generic error', () async {
      when(() => mockRepo.login(username: 'owner', password: 'wrong'))
          .thenThrow(const UnauthorizedException('Invalid credentials'));
      when(() => mockStorage.clearAll()).thenAnswer((_) async {});

      final success = await controller.login('owner', 'wrong');

      expect(success, isFalse);
      expect(controller.state.status, equals(AuthStatus.unauthenticated));
      expect(controller.state.errorMessage, equals('Invalid credentials'));
    });

    test('logout revokes token and clears storage', () async {
      when(() => mockStorage.getRefreshToken())
          .thenAnswer((_) async => 'stored_refresh');
      when(() => mockRepo.logout('stored_refresh')).thenAnswer((_) async {});
      when(() => mockStorage.clearAll()).thenAnswer((_) async {});

      await controller.logout();

      expect(controller.state.status, equals(AuthStatus.unauthenticated));
      verify(() => mockRepo.logout('stored_refresh')).called(1);
      verify(() => mockStorage.clearAll()).called(1);
    });
  });
}
